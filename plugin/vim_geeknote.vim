python3 import sys
python3 import vim
python3 sys.path.append(vim.eval('expand("<sfile>:h")'))

" ---------------------- Configuration ----------------------------------------

if has('nvim')
    let g:KeepNeovimMode='True'
endif

" ---------------------- Functions --------------------------------------------

function! Vim_KeepTerminate()
python3 << endOfPython
from vim_geeknote import KeepTerminate
KeepTerminate()
endOfPython
endfunction

function! Vim_KeepToggle()
python3 << endOfPython
from vim_geeknote import KeepToggle
KeepToggle()
endOfPython
endfunction

function! Vim_KeepActivateNode()
python3 << endOfPython
from vim_geeknote import KeepActivateNode
KeepActivateNode()
endOfPython
endfunction

function! Vim_KeepCloseNote(arg1)
python3 << endOfPython
from vim_geeknote import KeepCloseNote
filename = vim.eval("a:arg1")
KeepCloseNote(filename)
endOfPython
endfunction

function! Vim_KeepCreateNotebook(arg1)
python3 << endOfPython
from vim_geeknote import KeepCreateNotebook
name = vim.eval("a:arg1")
KeepCreateNotebook(name)
endOfPython
endfunction

function! Vim_KeepCreateNote(arg1)
python3 << endOfPython
from vim_geeknote import KeepCreateNote
name = vim.eval("a:arg1")
KeepCreateNote(name)
endOfPython
endfunction

function! Vim_KeepSaveAsNote()
python3 << endOfPython
from vim_geeknote import KeepSaveAsNote
KeepSaveAsNote()
endOfPython
endfunction

function! Vim_KeepSearch(arg1)
python3 << endOfPython
from vim_geeknote import KeepSearch
args = vim.eval("a:arg1")
KeepSearch(args)
endOfPython
endfunction

function! Vim_KeepPrepareToSaveNote(arg1)
python3 << endOfPython
from vim_geeknote import KeepPrepareToSaveNote
filename = vim.eval("a:arg1")
KeepPrepareToSaveNote(filename)
endOfPython
endfunction

function! Vim_KeepSaveNote(arg1)
python3 << endOfPython
from vim_geeknote import KeepSaveNote
filename = vim.eval("a:arg1")
KeepSaveNote(filename)
endOfPython
endfunction

function! Vim_KeepSync()
python3 << endOfPython
from vim_geeknote import KeepSync
KeepSync()
endOfPython
endfunction

function! Vim_KeepCommitStart()
python3 << endOfPython
from vim_geeknote import KeepCommitStart
KeepCommitStart()
endOfPython
endfunction

function! Vim_KeepCommitComplete()
python3 << endOfPython
from vim_geeknote import KeepCommitComplete
KeepCommitComplete()
endOfPython
endfunction

" ---------------------- User Commands ----------------------------------------

command!          Keep               call Vim_KeepToggle()
command! -nargs=1 KeepCreateNotebook call Vim_KeepCreateNotebook(<f-args>)
command! -nargs=1 KeepCreateNote     call Vim_KeepCreateNote(<f-args>)
command!          KeepSaveAsNote     call Vim_KeepSaveAsNote()
command! -nargs=* KeepSearch         call Vim_KeepSearch(<q-args>)
command!          KeepSync           call Vim_KeepSync()
