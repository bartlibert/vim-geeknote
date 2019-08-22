import re
import vim

from change import NoteRenamed
from view import KeepOpenNote
from conn import KeepGetNotes, KeepFindNoteCounts, KeepGetTags, KeepCreateNewNote, KeepRefreshNoteMeta, KeepGetAllNotes
from utils import (
    createTempFile,
    autocmd,
    isBufferModified,
    getActiveWindow,
    setActiveBuffer,
    setActiveWindow,
    numberwidth,
    foldcolumn,
    setWindowVariable,
    setBufferVariable,
    noremap
)

ExplorerCharOpened = u"\u25bd"
ExplorerCharClosed = u"\u25b6"

if int(vim.eval('exists("g:KeepExplorerNodeOpened")')):
    ExplorerCharOpened = vim.eval("g:KeepExplorerNodeOpened").decode("utf8")

if int(vim.eval('exists("g:KeepExplorerNodeClosed")')):
    ExplorerCharClosed = vim.eval("g:KeepExplorerNodeClosed").decode("utf8")

# A dictionary containing an entry for all nodes contained in the explorer
# window, keyed by guid.
registry = {}

# Maps GUIDs to instance numbers. Each node represents an object. Objects are
# unique but nodes are not. There can be any number nodes instanciated for an
# object.  An instance number is used to distinguish nodes for the same object.
# This container maps an object's GUID to the maximum instance number of any
# node representing the object (i.e. object node count minus one).
#
instanceMap = {}


def registerNode(node):
    guid = node.getId()
    if guid not in instanceMap:
        instance = 0
    else:
        instance = instanceMap[guid] + 1

    instanceMap[guid] = instance

    key = guid + "(" + str(instance) + ")"
    node.setKey(key)
    registry[key] = node


def deleteNodes():
    registry.clear()


def getNode(key):
    if key in registry:
        return registry[key]
    return None


def getNodeByInstance(guid, instance):
    key = guid + "(" + str(instance) + ")"
    return getNode(key)


class Node(object):
    def __init__(self, indent=0):
        self.parent = None
        self.children = []
        self.changes = []
        self.row = -1
        self.indent = indent
        self.prefWidth = 0
        self.key = ""
        self.close()

    def activate(self):
        self.toggle()

    def adapt(self, line):
        return False

    def addChild(self, node):
        node.parent = self
        self.children.append(node)

    def close(self):
        self.expanded = False

    def commitChanges(self):
        for change in self.changes:
            change.apply()
        del self.changes[:]

    def expand(self):
        self.expanded = True

    def getId(self):
        return "None"

    def getKey(self):
        return self.key

    def getPreferredWidth(self):
        if self.parent is None or self.parent.isExpanded():
            return self.prefWidth
        return 0

    def isExpanded(self):
        return self.expanded

    def isVisible(self):
        return self.row != -1

    def refresh(self):
        pass

    def setKey(self, key):
        self.key = key

    def removeChild(self, node):
        if node in self.children:
            self.children.remove(node)

    def setName(self, name):
        self.name = name

    def toggle(self):
        if self.expanded:
            self.close()
        else:
            self.expand()


class NoteNode(Node):
    def __init__(self, note, indent=1):
        super(NoteNode, self).__init__(indent)

        self.note = note
        self.title = note.title
        self.refresh()

    def adapt(self, line):
        # Was the note renamed?
        r = re.compile(
            "^\s+" "(.*)" "n\[.*\]" ".*$"  # leading whitespace  # note title  # key
        )  # everything else till end of line
        m = r.match(line)
        if m:
            title = m.group(1).strip()
            if self.title != title:
                change = NoteRenamed(self.note, title)
                self.changes.append(change)

                self.setTitle(title)
                return True
        return False

    def activate(self):
        super(NoteNode, self).activate()

        KeepOpenNote(self.note)

    def getId(self):
        return self.note.id

    def refresh(self):
        if self.title is not None:
            self.note = KeepRefreshNoteMeta(self.note)

        self.setTitle(self.note.title)

    def render(self, buffer, attribs):
        line = " " * (self.indent * 4) + self.title

        self.prefWidth = len(line)

        fmt = "{:<%d} n[{}]" % attribs["keyCol"]
        buffer.append(fmt.format(line, self.getKey()))
        self.row = len(buffer)

    def setTitle(self, title):
        if not title:
            summary = self.note.text.strip().split("\n")[0][:20]
            self.title = summary + ('..' if len(summary) > 20 else '')
        else:
            self.title = title


class TagNode(Node):
    def __init__(self, tag, indent=0):
        super(TagNode, self).__init__(indent)

        self.tag = tag
        self.loaded = False
        self.setName(tag.name)

    def addNote(self, note):
        node = NoteNode(note, self.indent + 1)
        registerNode(node)

        self.addChild(node)
        return node

    def expand(self):
        if self.loaded is False:
            notes = self.getNotes()
            notes.sort(key=lambda n: n.title)
            for note in notes:
                self.addNote(note)
            self.loaded = True

        super(TagNode, self).expand()

    def getId(self):
        return self.tag.id

    def getNotes(self):
        return KeepGetNotes(labels=[self.tag.name])

    def render(self, buffer, attribs):
        numNotes = len(self.children)

        if self.expanded:
            line = ExplorerCharOpened
        else:
            if self.loaded and numNotes == 0:
                line = ExplorerCharOpened
            else:
                line = ExplorerCharClosed

        line += " " + self.name
        if numNotes != 0:
            line += " (%d)" % numNotes

        self.prefWidth = len(line)

        fmt = "{:<%d} T[{}]" % attribs["keyCol"]
        buffer.append(fmt.format(line, self.getKey()))
        self.row = len(buffer)

        if self.expanded:
            for noteNode in self.children:
                noteNode.render(buffer, attribs)


class Explorer(object):
    def __init__(self):
        self.hidden = True
        self.selectedNode = None
        self.tags = []
        self.modifiedNodes = []
        self.dataFile = None
        self.buffer = None
        self.expandState = {}
        self.searchResults = []
        self.notes = []

        self.refresh()

        self.dataFile = createTempFile(prefix="__KeepExplorer__")

        autocmd("VimLeave", "*", ":call Vim_KeepTerminate()")

    def __del__(self):
        try:
            self.dataFile.close()
        except:
            pass

    def activateNode(self, line):
        key = self.getNodeKey(line)
        if key is not None:
            node = getNode(key)
            node.activate()

            # Rerender the navigation window. Keep the current cursor postion.
            row, col = vim.current.window.cursor
            self.render()
            vim.current.window.cursor = (row, col)

    def addNote(self, note):

        KeepCreateNewNote(note)
        self.render()
        # self.selectNode(node)

    def addSearchResults(self, results):
        for note in results:
            node = NoteNode(note, 0)
            registerNode(node)
            self.searchResults.append(node)

    def addTag(self, tag):
        tagNode = TagNode(tag)
        self.tags.append(tagNode)
        self.tags.sort(key=lambda t: t.tag.name.lower())

        registerNode(tagNode)

    def applyChanges(self):
        #
        # It is possible that user has rearranged (moved) the nodes since the
        # last time the changes were applied. Refresh them now.
        #
        self.updateNodeLineNumbers()

        # Look for nodes that were renamed
        for key in registry:
            node = getNode(key)
            if node.isVisible():
                if node.adapt(self.buffer[node.row]):
                    if node not in self.modifiedNodes:
                        self.modifiedNodes.append(node)

    def clearSearchResults(self):
        del self.searchResults[:]

    def commitChanges(self):
        if isBufferModified(self.buffer.number):
            self.applyChanges()

        for node in self.modifiedNodes:
            node.commitChanges()

        for node in self.modifiedNodes:
            for key in registry:
                tempNode = getNode(key)
                if tempNode.getId() == node.getId():
                    if tempNode.getKey() != node.getKey():
                        tempNode.refresh()

        del self.modifiedNodes[:]

    def getNodeParent(self, row):
        key = self.getNodeKey(self.buffer[row])
        node = getNode(key)

        # Only notes have parents
        if not isinstance(node, NoteNode):
            return None

        while row > 0:
            key = self.getNodeKey(self.buffer[row])
            if key is not None:
                node = getNode(key)
                if not isinstance(node, NoteNode):
                    return node
            row -= 1

        return None

    def getSelectedNode(self):
        if self.buffer is None:
            return None

        prevWin = getActiveWindow()
        setActiveBuffer(self.buffer)
        text = vim.current.line
        setActiveWindow(prevWin)

        key = self.getNodeKey(text)
        if key is not None:
            return getNode(key)
        return None

    def getMinWidth(self):
        maxWidth = 0
        for key in registry:
            width = getNode(key).getPreferredWidth()
            if width > maxWidth:
                maxWidth = width

        hpad = numberwidth() + foldcolumn() + 1
        return maxWidth + hpad

    def getNodeKey(self, nodeText):
        r = re.compile("^.+\[(.+)\]$")
        m = r.match(nodeText)
        if m:
            return m.group(1)
        return None

    #
    # Hide the navigation buffer. This closes the window it is displayed in but
    # does not destroy the buffer itself.
    #
    def hide(self):
        vim.command("{}bunload".format(self.buffer.number))
        self.hidden = True

    def initView(self):
        origWin = getActiveWindow()
        setActiveBuffer(self.buffer)

        wnum = getActiveWindow()
        bnum = self.buffer.number

        autocmd("BufWritePre", "<buffer>", ":call Vim_KeepCommitStart()")

        autocmd("BufWritePost", "<buffer>", ":call Vim_KeepCommitComplete()")

        setWindowVariable(wnum, "winfixwidth", True)
        setWindowVariable(wnum, "wrap", False)
        setWindowVariable(wnum, "cursorline", True)
        setBufferVariable(bnum, "swapfile", False)
        setBufferVariable(bnum, "bufhidden", "hide")

        vim.command("setfiletype geeknote")
        setActiveWindow(origWin)

    #
    # Is the navigation buffer hidden? When hidden, the buffer exists but is
    # not active in any window.
    #
    def isHidden(self):
        return self.hidden

    def refresh(self):
        self.saveExpandState()
        deleteNodes()

        self.noteCounts = KeepFindNoteCounts()

        del self.tags[:]
        tags = KeepGetTags()
        for tag in tags:
            self.addTag(tag)

        notes = KeepGetNotes(archived=False, trashed=False, pinned=False)
        del self.notes[:]
        for note in notes:
            print('note: {}')
            noteNode = NoteNode(note, 0)
            self.notes.append(noteNode)
            registerNode(noteNode)

        self.restoreExpandState()

    # Render the navigation buffer in the navigation window..
    def render(self):
        if self.buffer is None:
            return

        origWin = getActiveWindow()
        setActiveBuffer(self.buffer)

        # Before overwriting the navigation window, look for any changes made
        # by the user. Do not synchronize them yet with the server, just make
        # sure they are not lost.
        #
        if isBufferModified(self.buffer.number):
            self.applyChanges()

        # Clear the navigation buffer to get rid of old content (if any).
        del self.buffer[:]

        # Prepare rendering attributes
        attribs = {}
        attribs["keyCol"] = self.getMinWidth() + 1

        # Create separator
        fmt = "{:=^%d}" % (attribs["keyCol"] + 41)
        sep = fmt.format("=")

        # Prepare the new content and append it to the navigation buffer.
        content = []

        # Render notes, tags, and search results
        if len(self.notes) > 0:
            content.append("")
            content.append("Notes:")
            content.append(sep)

            for node in self.notes:
                node.render(content, attribs)

        if len(self.tags) > 0:
            content.append("")
            content.append("Tags:")
            content.append(sep)

            for node in self.tags:
                node.render(content, attribs)

        if len(self.searchResults) > 0:
            content.append("")
            content.append("Search Results:")
            content.append(sep)

            for node in self.searchResults:
                node.render(content, attribs)

        # Write the content list to the buffer starting at row zero.
        self.buffer.append(content, 0)

        # Move the cursor over the selected node (if any)
        if self.selectedNode is not None:
            if self.selectedNode.row != -1:
                vim.current.window.cursor = (self.selectedNode.row, 0)

        # Resize the window as appropriate.
        self.resize()

        #
        # Write the navigation window but disable BufWritePre events before
        # doing so. We only want to check for user changes when the user was
        # the one that saved the buffer.
        #
        ei = vim.eval("&ei")
        vim.command("set ei=BufWritePre")
        vim.command("write!")
        vim.command("set ei={}".format(ei))

        setActiveWindow(origWin)

    def resize(self):
        # Fix the width if requested.
        if int(vim.eval('exists("g:KeepExplorerWidth")')):
            width = int(vim.eval("g:KeepExplorerWidth"))
            vim.command("vertical resize %d" % width)
            return

        # Get the max allowable width (default is 40 columns)
        if int(vim.eval('exists("g:KeepMaxExplorerWidth")')):
            maxWidth = int(vim.eval("g:KeepMaxExplorerWidth"))
        else:
            maxWidth = 40

        # Get the minimum width needed to see all names/titles
        minWidth = self.getMinWidth()

        # Fix the width to the minimum of what is required vs. what is needed.
        width = min(minWidth, maxWidth)
        vim.command("vertical resize %d" % width)

    def restoreExpandState(self):
        for key in self.expandState:
            node = getNode(key)
            if node is not None:
                if self.expandState[key]:
                    node.expand()
                else:
                    node.close()

    def saveExpandState(self):
        for node in self.tags:
            self.expandState[node.getKey()] = node.expanded

    def selectNode(self, node):
        self.selectedNode = node

        # Move the cursor over the node if the node has been rendered.
        if node.row != -1:
            origWin = getActiveWindow()
            setActiveBuffer(self.buffer)
            vim.current.window.cursor = (node.row, 0)
            setActiveWindow(origWin)

    # Switch to the navigation buffer in the currently active window.
    def show(self):
        vim.command("topleft 50 vsplit {}".format(self.dataFile.name))
        self.buffer = vim.current.buffer

        self.initView()
        self.render()

        noremap("<silent> <buffer> <cr>", ":call Vim_KeepActivateNode()<cr>")

        self.hidden = False

    def updateNodeLineNumbers(self):
        for key in registry:
            getNode(key).row = -1

        for row in range(len(self.buffer)):
            line = self.buffer[row]
            key = self.getNodeKey(line)
            if key is not None:
                getNode(key).row = row
