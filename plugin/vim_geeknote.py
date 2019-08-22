import vim

from explorer import Explorer
from conn import KeepCreateNewNote, KeepLoadNote, KeepUpdateNote, KeepGetNotes
from view import KeepOpenNote, KeepGetOpenNote, KeepCommitChangesToNote, KeepCloseAllNotes
from note import Note

#
# +----------+---------------------------+
# |          |                           |
# |          |                           |
# | explorer |           view            |
# |          |                           |
# |          |                           |
# +----------+---------------------------+
#
# vim_geeknote.vim --> vim_geeknote.py --> explorer.py
#                                |            |
#                                |            |
#                                |            V
#                                +-------> view.py
#

explorer = Explorer()


def KeepActivateNode():
    explorer.activateNode(vim.current.line)


def KeepCommitStart():
    explorer.commitChanges()


def KeepCommitComplete():
    explorer.render()


def KeepCreateNote(title):
    # Cleanup the title of the note.
    title = title.strip("\"'")

    newnote = Note
    newnote.title = title
    newnote.text = ""

    note = KeepCreateNewNote(newnote)
    KeepOpenNote(note)

    # Add the note to the navigation window.
    explorer.addNote(note)


def KeepHandleNoteSaveFailure(note, e):
    print(e)
    msg = "+------------------- WARNING -------------------+\n"
    msg += "|                                               |\n"
    msg += "| Failed to save note (see error above)         |\n"
    msg += "|                                               |\n"
    msg += "| Save buffer to a file to avoid losing content |\n"
    msg += "|                                               |\n"
    msg += "+------------------- WARNING -------------------+\n"
    vim.command('echoerr "%s"' % msg)


def KeepSaveAsNote():
    global explorer

    title = ""
    rows = len(vim.current.buffer)
    if rows > 0:
        title = vim.current.buffer[0].strip()
    else:
        vim.command('echoerr "Cannot save empty note."')
        return

    content = ""
    if rows > 1:
        start = 1
        while start < rows:
            if vim.current.buffer[start].strip() != "":
                break
            start += 1
        for r in range(start, len(vim.current.buffer)):
            content += vim.current.buffer[r] + "\n"

        note = {}
        note.title = title
        note.text = content

    try:
        note = KeepCreateNewNote(note)
        note = KeepLoadNote(note)
    except Exception as e:
        KeepHandleNoteSaveFailure(note, e)
        return

    KeepOpenNote(note)

    # Add the note to the navigation window.
    explorer.addNote(note)


def KeepSaveNote(filename):
    note = KeepGetOpenNote(filename)
    changed = KeepCommitChangesToNote(note)
    if changed:
        try:
            KeepUpdateNote(note)
        except Exception as e:
            KeepHandleNoteSaveFailure(note, e)


def KeepSearch(args):
    notes = KeepGetNotes(searchWords=args)

    explorer.clearSearchResults()
    explorer.addSearchResults(notes)
    explorer.render()


def KeepSync():
    explorer.commitChanges()
    explorer.refresh()
    explorer.render()


def KeepTerminate():
    KeepCloseAllNotes()


def KeepToggle():
    global explorer

    if explorer.isHidden():
        explorer.show()
    else:
        explorer.hide()
