import gi
import datetime
import neovim
import tempfile
# from threading import Thread
import threading
from functools import partial
from dream_dtb import config

# from sqlalchemy.event import listen
# from sqlalchemy.pool import Pool

# from dream_dtb import db
from dream_dtb import util
from dream_dtb.db import Dream
from dream_dtb.db import DreamDAO
from dream_dtb.db import Tag
from dream_dtb.db import DreamType
gi.require_version('Gtk', '3.0')
gi.require_version('Vte', '2.91')
from gi.repository import Gtk, Gio, Vte, GLib, GObject


class RpcEventHandler():
    """Manage nvim loop for handling rpc events
    """

    def __init__(self, nvim: object, func_req, func_not):
        # self.stop_running = threading.Event()
        self.loop_thread = threading.Thread(target=nvim.run_loop, args=(func_req, func_not))

    def start(self):
        self.loop_thread.start()

    def stop(self):
        print("start join")
        self.loop_thread.join()
        print("stop join")


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

    def add(self, bufname, **kwargs):
        # TODO: pass parameters as a dictionnary **kwarg and check parameters
        # at least date and title should exists otherwise error
        """ add a buffer to the bufs stack """
        # TODO: should I check if self.bufs[bufname] exists and report to log
        # if it does
        self.bufs[bufname] = {'modified': False,
                              'instance': {'id': kwargs['id'],
                                           'title': kwargs['title'],
                                           'date': kwargs['date'],
                                           'recit': kwargs['recit'],
                                           'tags': kwargs['tags'],
                                           'drtype': kwargs['drtype']}}

    def modify(self, bufname, **kwargs):
        """ modify a buffer
        Arguments:
            - bufname (str): name of the buffer
            - instance (dict): {'id': id,
                                'title': title,
                                'date': date,
                                'recit': recit,
                                'tags': tags,
                                'drtype': drtype}
                                instance can contains one or all of the above
                                metionned keys
        """
        # TODO: should I check if self.bufs[bufname] exists and report to log
        # if it does not
        # TODO: Don't set modified to True if field before = field after ?
        self.bufs[bufname]['modified'] = True
        for key in kwargs:
            self.bufs[bufname]['instance'][key] = kwargs[key]

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
                print("start create record")
                DreamDAO.create(buf['instance'])
                print("stop create record")
                print("dream created in database")
            else:
                DreamDAO.update(buf['instance']['id'], buf['instance'])
            self.bufs[bufname]['modified'] = False

    def get_ids(self):
        idnum = []
        for elem in self.bufs:
            idnum.append(self.bufs[elem]['instance']['id'])
        return idnum

    def get_bufname(self, idNum):
        """ Return buffername which correspond to idNum """
        dict_tmp = {k: v for k, v in self.bufs.items() if v['instance']['id'] == idNum}
        for elem in dict_tmp:
            return elem

    def save_all(self):
        # print(self.bufs)
        print("save all!")
        for elem in list(self.bufs):
            print("save: ", elem)
            self.save(elem)

    def remove(self, bufname):
        """ remove a buffer from the buffer stack """
        print("buffer removed")
        # pass


class Model:
    def __init__(self):
        self.myMoney = Observable(0)
        self.myTree = Observable()
        self.myBuff = Buffer()

    def addMoney(self, value):
        self.myMoney.set(self.myMoney.get() + value)

    def removeMoney(self, value):
        self.myMoney.set(self.myMoney.get() - value)

    def getDreamItems(self):
        items = []
        date_tmp = None
        with util.session_scope() as session:
            # TODO: order record by creation date instead of title
            # TODO: make tree by year-->month-->day-->dream(s) instead of the
            # current year-month-day-->dream(s)
            for inst in session.query(Dream).order_by(Dream.date, Dream.title):
                # print(i)
                # print(items)
                date = inst.date.strftime('%Y-%m-%d')
                if date == date_tmp:
                    items[last_ind].append([inst.title, inst.id])
                else:
                    items.append([date, [inst.title, inst.id]])
                    last_ind = len(items) - 1
                date_tmp = date
        return(items)

    def updateTree(self):
        self.myTree.set(self.getDreamItems())


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
        # there is always the scrollbar (otherwise: AUTOMATIC - only if needed
        # - or NEVER)
        self.scrolled_window.set_policy(
            Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        self.liststore_tags = Gtk.ListStore(str)
        with util.session_scope() as session:
            for inst in session.query(Tag):
                self.liststore_tags.append([inst.label])

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
        with util.session_scope() as session:
            for inst in session.query(DreamType):
                self.drtype_entry.insert_text(-1, inst.label)

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
            print("no item selected !")


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
            print("nvim attached")
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
        print("init nvim")
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
            with open(args[1], 'r') as myfile:
                data = myfile.read()
            self.event_callback['Save'](args[1], recit=data)
            print(f'{args[1]} saved !')
        if sub == 'DreamGuiEvent' and args[0] == 'Quit':
            self.event_callback['Quit']()
            print('vim quit event')

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

        # button = Gtk.Button()
        # icon = Gio.ThemedIcon(name="mail-send-receive-symbolic")
        # image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.BUTTON)
        # button.add(image)
        # self.pack_end(button)
        # self.close = Gtk.Button()
        # self.close.set_relief(Gtk.ReliefStyle.NONE)
        # img = Gtk.Image.new_from_icon_name("window-close-symbolic", Gtk.IconSize.MENU)
        # self.close.set_image(img)
        # self.close.connect("clicked", Gtk.main_quit)
        # self.pack_end(self.close)

        # seperator = Gtk.Separator.new(Gtk.Orientation.VERTICAL)
        # self.pack_end(seperator)

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=1)
        # Gtk.StyleContext.add_class(box.get_style_context(), "linked")

        self.newdream = Gtk.Button(label="New dream")
        box.add(self.newdream)

        button = Gtk.Button("Save all")
        box.add(button)

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

    def SetMoney(self, money):
        self.moneyCtrl.delete(0, 'end')
        self.moneyCtrl.insert('end', str(money))

    def SetTree(self, items):
        self.navigationbar.store.clear()
        for item in items:
            piter = self.navigationbar.store.append(None, [item[0], -1])
            for dream in item[1:len(item)]:
                self.navigationbar.store.append(piter, dream)


class Controller:
    def __init__(self):
        # Create view and model
        self.model = Model()
        self.view = View()

        # Add callback to the model
        self.model.myTree.addCallback(self.TreeChanged)

        # Add callback for neovim rpc event
        self.view.edit.event_callback['Save'] = self.model.myBuff.modify
        self.view.edit.event_callback['Quit'] = self.model.myBuff.save_all
        # self.model.myTree.addCallback(self.MoneyChanged)

        # Configure widgets events
        # self.MoneyChanged(self.model.myMoney.get())
        # self.view.navigationbar.tree.bind("<Double-1>", self.OnDoubleClick)
        self.view.connect("delete-event", self.on_close_main)
        # self.view.menubar.close.connect("clicked", self.on_close_clicked)
        self.view.edit.terminal.connect("child-exited", self.child_exited)
        self.view.navigationbar.tree.connect("row-activated", self.on_tree_double_click)
        self.view.menubar.newdream.connect("clicked", self.on_newdream_click)
        # self.select = self.view.navigationbar.tree.get_selection()
        # self.select.connect("row-activated", self.on_tree_selection_changed)
        # self.view.menubar.connect("")

        # Init the view
        # TODO: I should call self.TreeChanged(self.model.myTree.get()) ?
        self.model.myTree.set(self.model.getDreamItems())
        # self.TreeChanged(self.model.myTree.get())

        self.view.show_all()

    def on_close_main(self, *args):
        print("close event")
        self.view.edit.nvim.command('xa!', async=True)
        # The default behavior is to propagate the close signal into the
        # destroy event. To stop the propagation the handler must return True
        return True

    def on_close_clicked(self, *args):
        self.view.edit.nvim.command('xa!', async=True)

    def on_newdream_click(self, *args):
        dialog = DreamDialog(self.view)
        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            print("The OK button of the newdream dialog was clicked")
            print(f'date: {dialog.date_entry.get_date()}')
            print(f'title: {dialog.title_entry.get_text()}')
            print(f'dream type: {dialog.drtype_entry.get_active_text()}')
            tag_tmp = []
            for row in dialog.liststore_tags_entry:
                if row[0] not in tag_tmp:
                    tag_tmp.append(row[0])
            print(f'tags: {tag_tmp}')
            year, month, day = dialog.date_entry.get_date()
            date = datetime.datetime.strptime(f'{year}{month}{day}', "%Y%m%d")
            # TODO: check that the combination (date, title) does not already
            # exists in bufs
            tmpfile = tempfile.mkstemp(dir=config.BUF_PATH)
            with open(tmpfile[1], "w") as text_file:
                print("", file=text_file, end='')
            self.model.myBuff.add(tmpfile[1], id=None,
                                  title=dialog.title_entry.get_text(),
                                  date=date,
                                  recit="",
                                  tags=tag_tmp,
                                  drtype=dialog.drtype_entry.get_active_text())
            self.view.edit.nvim.command(f'edit {tmpfile[1]}', async=True)
        elif response == Gtk.ResponseType.CANCEL:
            print("The Cancel button of the newdream dialog was clicked")

        dialog.destroy()

    def child_exited(self, *args):
        # self.view.edit.nvim.command('call dreamdtb#notify_quit_vim()', async=True)
        print("on child exited")
        self.view.edit.nvim_loop.stop()
        self.view.destroy()
        Gtk.main_quit()

    def on_tree_double_click(self, tree_view, path, column):
        """ callback when an item of the treeview has been double-clicked
        """
        if path.get_depth() == 2:
            print("double click on dream id: {}".format(self.view.navigationbar.store[path][1]))
            inst = DreamDAO.find_by_id(self.view.navigationbar.store[path][1])
            if inst['id'] not in self.model.myBuff.get_ids():
                tmpfile = tempfile.mkstemp(dir=config.BUF_PATH)
                with open(tmpfile[1], "w") as text_file:
                    print(inst['recit'], file=text_file, end='')
                self.model.myBuff.add(tmpfile[1], id=inst['id'],
                                      title=inst['title'],
                                      date=inst['date'],
                                      recit=inst['recit'],
                                      tags=inst['tags'],
                                      drtype=inst['drtype'])
                self.view.edit.nvim.command(f'edit {tmpfile[1]}', async=True)
            else:
                print(f"instance:{inst.id} already in buff")
                tmp_val = self.model.myBuff.get_bufname(inst.id)
                self.view.edit.nvim.command(f'buffer {tmp_val}', async=True)
        else:
            print("double click on date")

    def AddDream(self):
        # TODO: copy code from on_tree_double_click, add callback and custom
        # signal
        pass

    def AddMoney(self):
        self.model.addMoney(10)

    def RemoveMoney(self):
        self.model.removeMoney(10)

    def MoneyChanged(self, money):
        self.view.SetMoney(money)

    def TreeChanged(self, items):
        self.view.SetTree(items)

    def RunGui(self):
        Gtk.main()

# pour les evenements de changement dans la bdd
# http://docs.sqlalchemy.org/en/latest/core/event.html

# doc de base
# https://python-gtk-3-tutorial.readthedocs.io/en/latest/layout.html#notebook
# https://developer.gnome.org/gnome-devel-demos/unstable/treeview_treestore.py.html.en

# TODO: vte_terminal_spawn_sync has been deprecated since version 0.48 and
# should not be used in newly-written code.  Use vte_terminal_spawn_async()
# instead. Not sure what my version is, but vte_terminal_spawn_async is not
# available.
# TODO: implement a logger instead of printing to stdout
# TODO: implement all query statements in the corresponding DAO ???
# https://developer.gnome.org/gtk3/3.10/ch28s02.html
