import gi
import datetime
import neovim
import tempfile
import logging
import threading
from functools import partial
from dream_dtb import config

from dream_dtb.db import DreamDAO
from dream_dtb.db import TagDAO
from dream_dtb.db import DreamTypeDAO
gi.require_version('Gtk', '3.0')
gi.require_version('Vte', '2.91')
from gi.repository import Gtk, Gio, Vte, GLib, GObject


logger = logging.getLogger('dream_logger')


class RpcEventHandler():
    """Manage nvim loop for handling rpc events
    """

    def __init__(self, nvim: object, func_req, func_not):
        self.loop_thread = threading.Thread(target=nvim.run_loop, args=(func_req, func_not))

    def start(self):
        self.loop_thread.start()

    def stop(self):
        logger.info("waiting for nvim loop to finish...")
        self.loop_thread.join()
        logger.info("nvim loop finished")


class Observable:
    def __init__(self, initialValue=None):
        self.data = initialValue
        self.callbacks = {}

    def addCallback(self, func):
        self.callbacks[func] = 1

    def delCallback(self, func):
        del self.callbacks[func]

    def _docallbacks(self):
        for func in self.callbacks:
            func(self.data)

    def set(self, data):
        self.data = data
        self._docallbacks()

    def get(self):
        return self.data

    def unset(self):
        self.data = None


class Buffer():
    """ class representing a list of currently edited buffers (id, tags, dream
    type, title, recit, date) whether one of the field have been modified or
    not.  If the dream is not already present in the database id is None.
    """

    def __init__(self):
        self.bufs = {}

    def add(self, instance):
        """ add a buffer to the bufs stack """
        tmpfile = tempfile.mkstemp(dir=config.BUF_PATH)[1]
        with open(tmpfile, "w") as text_file:
            print(instance['recit'], file=text_file, end='')
        self.bufs[tmpfile] = {'modified': False,
                              'instance': instance}
        return tmpfile

    def modify(self, bufname, instance):
        """ modify a buffer
        Arguments:
            - bufname (str): name of the buffer
            - instance (dict): {'title': title,
                                'date': date,
                                'recit': recit,
                                'tags': tags,
                                'drtype': drtype}
        """
        # TODO: Don't set modified to True if field before = field after
        self.bufs[bufname]['modified'] = True
        for key in instance:
            self.bufs[bufname]['instance'][key] = instance[key]

    def save(self, bufname):
        """ Save a buffer to the database """
        # TODO: make save private --> _save(self, bufname) ?
        # TODO: if buf['instance']['recit'] == '', should I discard writing to
        # database an empty dream ? or maybe remove the dream from the database
        # if it already exists
        # TODO: put the line into a try catch block to be sure it exists.
        # Otherwise report to log
        buf = self.bufs[bufname]
        if buf['modified']:
            if buf['instance']['id'] is None:
                logger.info("create record...")
                DreamDAO.create(buf['instance'])
                logger.info("done creating record")
            else:
                logger.info("modify record...")
                DreamDAO.update(buf['instance']['id'], buf['instance'])
                logger.info("done modifying record")
            self.bufs[bufname]['modified'] = False

    def get_ids(self):
        idnum = []
        for elem in self.bufs:
            idnum.append(self.bufs[elem]['instance']['id'])
        return idnum

    def get_bufname(self, idnum):
        """ Return buffername which correspond to idnum """
        dict_tmp = {k: v for k, v in self.bufs.items() if v['instance']['id'] == idnum}
        for elem in dict_tmp:
            return elem

    def save_all(self):
        logger.info("save all buffer!")
        for elem in list(self.bufs):
            logger.info(f'save: {elem}')
            self.save(elem)

    def remove(self, bufname):
        """ remove a buffer from the buffer stack """
        print("buffer removed")


class Model:
    def __init__(self):
        self.myTree = Observable(DreamDAO.get_tree())
        self.myCurBuff = Observable()
        self.myBuffList = Buffer()

    def updateTree(self):
        self.myTree.set(DreamDAO.get_tree())

    def addDreamBuff(self, instance):
        return self.myBuffList.add(instance)

    def setDreamMeta(self, bufname, instance):
        self.myBuffList.modify(bufname, instance)

    def setCurBuff(self, bufname):
        self.myCurBuff.set(bufname)

    def getCurBuff(self):
        return self.myCurBuff.get()

    def get_inst_buf(self, bufname):
        return self.myBuffList.bufs[bufname]['instance']

    def get_ids(self):
        return self.myBuffList.get_ids()

    def get_buf_by_id(self, idnum):
        return self.myBuffList.get_bufname(idnum)


class DreamDialog(Gtk.Dialog):
    def __init__(self, parent):
        Gtk.Dialog.__init__(self, "New dream dialog", parent, 0,
                            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                             Gtk.STOCK_OK, Gtk.ResponseType.OK))

        self.set_default_size(150, 100)
        self.set_border_width(10)

        self.box = self.get_content_area()

        self.date_label = Gtk.Label('Date:')
        self.date_entry = Gtk.Calendar()

        self.title_label = Gtk.Label('Title:')
        self.title_entry = Gtk.Entry()

        self.tags_label = Gtk.Label('Tags:')

        self.scrolled_window = Gtk.ScrolledWindow()
        self.scrolled_window.set_border_width(2)
        self.scrolled_window.set_policy(
            Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        self.liststore_tags = Gtk.ListStore(str)
        for label in TagDAO.get_labels():
                self.liststore_tags.append([label])

        self.liststore_tags_entry = Gtk.ListStore(str)
        self.tags_entry = Gtk.TreeView(model=self.liststore_tags_entry)
        self.tags_entry.set_grid_lines(Gtk.TreeViewGridLines.BOTH)
        self.tags_entry.props.expand = True

        renderer_combo = Gtk.CellRendererCombo()
        renderer_combo.set_property("editable", True)
        renderer_combo.set_property("model", self.liststore_tags)
        renderer_combo.set_property("text-column", 0)
        renderer_combo.set_property("has-entry", True)
        renderer_combo.connect("edited", self.on_combo_changed)

        self.column_combo = Gtk.TreeViewColumn("0 tag(s)", renderer_combo, text=0)
        self.tags_entry.append_column(self.column_combo)

        # used to prevent a gtk warning bug
        # https://stackoverflow.com/questions/46253472/allocating-size-to-gtk-warning-when-using-gtk-treeview-inside-gtk-scrolledw
        grid = Gtk.Grid()
        grid.attach(self.tags_entry, 0, 0, 1, 1)
        self.scrolled_window.add(grid)

        self.tag_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=1)
        self.add_tag = Gtk.Button(label="Add tag")
        self.add_tag.connect("clicked", self.on_add_tag_clicked)
        self.rm_tag = Gtk.Button(label="Remove tag")
        self.rm_tag.connect("clicked", self.on_rm_tag_clicked)

        self.drtype_label = Gtk.Label('Dream type:')
        self.drtype_entry = Gtk.ComboBoxText.new_with_entry()
        for label in DreamTypeDAO.get_labels():
                self.drtype_entry.insert_text(-1, label)

        self.tag_button_grid = Gtk.Grid()
        self.tag_button_grid.props.row_homogeneous = True
        self.tag_button_grid.attach(self.scrolled_window, 0, 0, 2, 3)
        self.tag_button_grid.attach_next_to(self.add_tag, self.scrolled_window,
                                            Gtk.PositionType.BOTTOM, 1, 1)
        self.tag_button_grid.attach_next_to(self.rm_tag, self.add_tag,
                                            Gtk.PositionType.RIGHT, 1, 1)

        self.box.add(self.date_label)
        self.box.add(self.date_entry)
        self.box.add(self.title_label)
        self.box.add(self.title_entry)
        self.box.add(self.tags_label)
        self.box.add(self.tag_button_grid)
        self.box.add(self.drtype_label)
        self.box.add(self.drtype_entry)
        self.box.props.spacing = 2

        self.show_all()

    def _set_title(self, title):
        self.title_entry.set_text(title)

    def _set_date(self, year, month, day):
        self.date_entry.select_month(month, year)
        self.date_entry.select_day(day)

    def _set_tags(self, tags):
        """
        Arguments:
                - tags list(str)
        """
        for tag in tags:
            self.liststore_tags_entry.append([tag])

    def _set_drtype(self, drtype):
        """
        Arguments:
                - drtype (str)
        """
        self.drtype_entry.get_child().set_text(drtype)

    def set_dialog(self, instance):
        """ Set dialog fields
        """
        self._set_title(instance['title'])
        self._set_date(*list(map(int, instance['date'].strftime("%Y-%m-%d").split('-'))))
        self._set_tags(instance['tags'])
        self._set_drtype(instance['drtype'])

    def _get_dialog(self):
        """ Get dialog fields
        """
        instance = {}

        tags = []
        for row in self.liststore_tags_entry:
            if row[0] not in tags and row[0].strip():
                tags.append(row[0])
        instance['tags'] = tags

        year, month, day = self.date_entry.get_date()
        instance['date'] = datetime.datetime.strptime(f'{year}{month}{day}', "%Y%m%d").date()

        instance['title'] = self.title_entry.get_text()
        instance['drtype'] = self.drtype_entry.get_active_text()

        return instance

    def spawn(self):
        """ spawn dialog
        """
        instance = None
        response = self._run()

        if response == Gtk.ResponseType.OK:
            logger.info("The OK button was clicked")
            instance = self._get_dialog()
        elif response == Gtk.ResponseType.CANCEL:
            logger.info("The Cancel button was clicked")

        self._destroy()

        return instance

    def _run(self):
        """ Run self
        """
        response = self.run()
        return response

    def _destroy(self):
        """ Destroy self
        """
        self.destroy()

    def on_combo_changed(self, widget, path, text):
        self.liststore_tags_entry[path][0] = text

    def on_add_tag_clicked(self, *args):
        self.liststore_tags_entry.append(["new tag"])
        new_title = self.column_combo.get_title()
        new_title = new_title.split(sep=' ')
        new_title = f'{int(new_title[0])+1} {new_title[1]}'
        self.column_combo.set_title(new_title)
        self.box = self.get_content_area()

    def on_rm_tag_clicked(self, *args):
        model, treeiter = self.tags_entry.get_selection().get_selected()
        if treeiter is not None:
            new_title = self.column_combo.get_title()
            new_title = new_title.split(sep=' ')
            new_title = f'{int(new_title[0])-1} {new_title[1]}'
            self.column_combo.set_title(new_title)
            self.liststore_tags_entry.remove(treeiter)
        else:
            logger.info("no item selected !")


class Editor(Gtk.Frame):
    """ A Frame containing a Vte terminal widget running neovim
    """
    def __init__(self):
        """ Create a terminal widget and connect it to the Frame
        """
        super().__init__()
        self.terminal = Vte.Terminal(is_focus=True,
                                     has_focus=True,
                                     scrollback_lines=0,
                                     scroll_on_output=False,
                                     scroll_on_keystroke=True,
                                     rewrap_on_resize=False)
        self.add(self.terminal)
        self.event_callback = {}

    def spawn(self, addr, argv=None):
        """
        Spawn a child process (neovim) into the terminal widget

        addr: socket address to connect nvim api to
        argv: list(str): arguments passed to the nvim command
        rtp: (str): path to additional runtime vim file
        """
        def callback(*args):
            """ Callback called only once for connecting to the neovim instance
            and for additional nvim configuration.
            """
            self.terminal.disconnect(once)
            self.nvim = neovim.attach('socket', path=addr)
            logger.info("nvim attached")
            self.emit('nvim-setup', self.nvim)
        once = self.terminal.connect('cursor-moved', callback)
        self.terminal.spawn_sync(Vte.PtyFlags.DEFAULT,
                                 None,
                                 ['nvim', *argv],
                                 [f'NVIM_LISTEN_ADDRESS={addr}'],
                                 GLib.SpawnFlags.SEARCH_PATH,
                                 None,
                                 None,
                                 None)

    @GObject.Signal(flags=GObject.SignalFlags.RUN_LAST)
    def nvim_setup(self, nvim: object):
        """ Custom signal 'nvim_setup' used for initilizing some nvim options
        """
        logger.info("init nvim")
        nvim.subscribe('DreamGuiEvent')
        nvim.vars['gui_channel'] = nvim.channel_id
        nvim.command(f'set rtp^={config.NVIM_RUNTIME}', async=True)
        nvim.command('runtime! ginit.vim', async=True)
        self.nvim_loop = RpcEventHandler(nvim,
                                         partial(self.emit, 'nvim-request', nvim),
                                         partial(self.emit, 'nvim-notify', nvim))
        self.nvim_loop.start()

    @GObject.Signal(flags=GObject.SignalFlags.RUN_LAST)
    def nvim_notify(self, nvim: object, sub: str, args: object):
        """ neovim rpcnotify events handler """
        if sub == 'DreamGuiEvent' and args[0] == 'Save':
            logger.info('notify save event')
            instance = {}
            with open(args[1], 'r') as myfile:
                data = myfile.read()
            instance['recit'] = data
            self.event_callback['Save'](args[1], instance)
            logger.info(f'{args[1]} saved !')
        if sub == 'DreamGuiEvent' and args[0] == 'Quit':
            logger.info('notify quit event')
            self.event_callback['Quit']()
        if sub == 'DreamGuiEvent' and args[0] == 'Current':
            logger.info('notify current event')
            self.event_callback['Current'](args[1])

    @GObject.Signal(flags=GObject.SignalFlags.RUN_LAST)
    def nvim_request(self, nvim: object, sub: str, args: object):
        """ neovim rpcrequest events handler """
        pass


class NavigationTree(Gtk.Frame):
    def __init__(self):
        super().__init__()
        self.store = Gtk.TreeStore(str, int)
        self.tree = Gtk.TreeView(self.store)

        self.renderer = Gtk.CellRendererText()
        self.column = Gtk.TreeViewColumn("Dreams", self.renderer, text=0)
        self.tree.append_column(self.column)
        # emit 'row-activated signal on double click instead of default single
        # click
        self.tree.set_activate_on_single_click = False
        self.add(self.tree)


class MenuBar(Gtk.HeaderBar):
    def __init__(self):
        super().__init__()
        self.set_show_close_button(True)

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=1)
        # Gtk.StyleContext.add_class(box.get_style_context(), "linked")

        self.newdream = Gtk.Button(label="New dream")
        box.add(self.newdream)

        self.moddream = Gtk.Button(label="Modify dream")
        box.add(self.moddream)

        self.pack_start(box)


class View(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self)
        self.createUI()

    def createUI(self):
        self.set_property("title", "Dream note")
        self.set_border_width(1)
        self.set_default_size(800, 600)

        self.paned = Gtk.Paned.new(Gtk.Orientation.HORIZONTAL)
        self.paned.set_wide_handle = True
        self.add(self.paned)

        self.menubar = MenuBar()
        self.menubar.props.title = self.get_property("title")
        self.set_titlebar(self.menubar)

        self.navigationbar = NavigationTree()
        self.navigationbar.set_shadow_type = Gtk.ShadowType(1)

        self.edit = Editor()
        self.edit.set_shadow_type = Gtk.ShadowType(1)
        self.edit.spawn(config.IPC_PATH, '')

        self.paned.add1(self.navigationbar)
        self.paned.add2(self.edit)

    def SetTree(self, tree):
        self.navigationbar.store.clear()
        for year in tree:
            piter = self.navigationbar.store.append(None, [year, -1])
            for month in tree[year]:
                piter2 = self.navigationbar.store.append(piter, [month, -1])
                for day in tree[year][month]:
                    piter3 = self.navigationbar.store.append(piter2, [day, -1])
                    for dream in tree[year][month][day]:
                        self.navigationbar.store.append(piter3, dream)

    def SetCurBuffer(self, bufname):
        self.edit.nvim.command(f'edit {bufname}', async=True)


class Controller:
    def __init__(self):
        # Create view and model
        self.model = Model()
        self.view = View()

        # Add callback to the model
        self.model.myTree.addCallback(self.TreeChanged)
        self.model.myCurBuff.addCallback(self.CurBuffChanged)

        # Add callback for neovim rpc event
        self.view.edit.event_callback['Save'] = self.model.myBuffList.modify
        self.view.edit.event_callback['Quit'] = self.model.myBuffList.save_all
        # modify Observable without triggering the Observable callbacks
        self.view.edit.event_callback['Current'] = (lambda x: setattr(self.model.myCurBuff, 'data', x))

        # Configure widgets events
        self.view.connect("delete-event", self.on_close_main)
        self.view.edit.terminal.connect("child-exited", self.on_child_exit)
        self.view.navigationbar.tree.connect("row-activated", self.on_tree_double_click)
        self.view.menubar.newdream.connect("clicked", self.on_newdream_click)
        self.view.menubar.moddream.connect("clicked", self.on_moddream_click)

        # Init the view
        self.TreeChanged(self.model.myTree.get())

        self.view.show_all()

    def on_close_main(self, *args):
        logger.info("close event")
        self.view.edit.nvim.command('xa!', async=True)
        # The default behavior is to propagate the close signal into the
        # destroy event. To stop the propagation the handler must return True
        return True

    def on_moddream_click(self, *args):
        logger.info("modify dream clicked")
        dialog = DreamDialog(self.view)
        bufname = self.model.getCurBuff()
        dialog.set_dialog(self.model.get_inst_buf(bufname))

        instance = dialog.spawn()

        if instance is not None:
            self.DreamMetaChanged(bufname, instance)

    def on_newdream_click(self, *args):
        logger.info("add dream clicked")
        dialog = DreamDialog(self.view)

        instance = dialog.spawn()

        if instance is not None:
            instance['id'] = None
            instance['recit'] = ''
            self.AddDream(instance)

    def on_child_exit(self, *args):
        logger.info("nvim exited")
        self.view.edit.nvim_loop.stop()
        self.view.destroy()
        Gtk.main_quit()

    def on_tree_double_click(self, tree_view, path, column):
        """ callback when an item of the treeview has been double-clicked
        """
        if path.get_depth() == 4:
            logger.info(f'double click on dream id: {self.view.navigationbar.store[path][1]}')
            instance = DreamDAO.find_by_id(self.view.navigationbar.store[path][1])
            if instance['id'] not in self.model.get_ids():
                self.AddDream(instance)
            else:
                logger.info(f"instance: {instance['id']} already in bufflist")
                tmp_val = self.model.myBuffList.get_bufname(instance['id'])
                bufname = self.model.get_buf_by_id(instance['id'])
                self.model.setCurBuff(bufname)
        else:
            logger.info("double click on date (year, month, or day)")

    def AddDream(self, instance):
        bufname = self.model.addDreamBuff(instance)
        self.model.setCurBuff(bufname)

    def DreamMetaChanged(self, bufname, instance):
        self.model.setDreamMeta(bufname, instance)

    def TreeChanged(self, tree):
        self.view.SetTree(tree)

    def CurBuffChanged(self, bufname):
        self.view.SetCurBuffer(bufname)

    def RunGui(self):
        Gtk.main()

# pour les evenements de changement dans la bdd
# http://docs.sqlalchemy.org/en/latest/core/event.html

# doc de base
# https://python-gtk-3-tutorial.readthedocs.io/en/latest/layout.html#notebook
# https://developer.gnome.org/gnome-devel-demos/unstable/treeview_treestore.py.html.en
# https://developer.gnome.org/gtk3/3.10/ch28s02.html

# TODO: vte_terminal_spawn_sync has been deprecated since version 0.48 and
# should not be used in newly-written code.  Use vte_terminal_spawn_async()
# instead. Not sure what my version is, but vte_terminal_spawn_async is not
# available.
# TODO: trigger TreeChanged on db modified
