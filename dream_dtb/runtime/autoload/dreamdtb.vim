function! dreamdtb#notify_save_buffer()
  " notify client after buffer has been saved
  let s:bufname=expand('<afile>')
  call rpcnotify(g:gui_channel, 'DreamGuiEvent', 'Save', s:bufname)
endfunction

function! dreamdtb#notify_quit_vim()
  " notify client after vim has been quited
  call rpcnotify(g:gui_channel, 'DreamGuiEvent', 'Quit')
endfunction
