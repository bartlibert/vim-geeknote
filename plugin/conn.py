import gkeepapi
from note import Note

gkeep = gkeepapi.Keep()
gkeep.login('lapino@gmail.com', 'llhrtnvwfogesgeo')
# authToken = gkeep.authToken
# noteStore = gkeep.getNoteStore()


def KeepCreateNewNote(note):
    return gkeep.createNote(note.title, note.text)


def KeepFindNoteCounts():
    return len(gkeep.all())


def KeepGetNotes(searchWords=None, labels=None, archived=None, trashed=False, colors=None, pinned=None):
    notes = []
    for gnote in gkeep.find(query=searchWords, labels=labels, colors=colors, pinned=pinned, archived=archived,
                            trashed=trashed):
        note = Note(title=gnote.title, text=gnote.text, id=gnote.server_id)
        notes.append(note)

    return notes

def KeepGetAllNotes():
    return gkeep.all()


def KeepGetTags():
    return gkeep.labels()


def KeepLoadNote(note):
    return gkeep.get(note.id)


def KeepRefreshNoteMeta(note):
    return gkeep.get(note.id)


def KeepUpdateNote(note):
    update = KeepLoadNote(note)
    update.title = note.title
    update.text = note.text
