augroup dreamdtbgui
  autocmd!
  autocmd BufWritePost * call dreamdtb#notify_save_buffer()
  autocmd VimLeave * call dreamdtb#notify_quit_vim()
augroup END

