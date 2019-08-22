from conn import KeepUpdateNote


class Change(object):
    def apply(self):
        pass


class NoteRenamed(Change):
    def __init__(self, note, newTitle):
        self.note = note
        self.newTitle = newTitle

    def apply(self):
        self.note.title = self.newTitle
        KeepUpdateNote(self.note)
