augroup dreamdtbgui
  autocmd!
  " au DirChanged,BufEnter,BufLeave * cal nvim_pygtk3#notify_bufs()
  " au TermOpen * cal nvim_pygtk3#notify_bufs()
  " au TextChanged,TextChangedI,BufWritePost * cal nvim_pygtk3#notify_bufs()
  " au DirChanged,BufEnter,BufLeave * cal nvim_pygtk3#notify_tabs()
  " au ColorScheme * cal nvim_pygtk3#notify_colors()
  " autocmd BufNewFile,BufWrite,OptionSet,TextChanged,TextChangedI * call dreamdtb#notify_buffer()
  autocmd BufWritePost * call dreamdtb#notify_save_buffer()
  " autocmd BufDelete,BufWipeout,BufUnload * call dreamdtb#notify_quit_buffer()
  autocmd VimLeave * call dreamdtb#notify_quit_vim()
  " autocmd FileChangedShell * call dreamdtb#notify_save_buffer()
augroup END

