import click
from click_default_group import DefaultGroup
import datetime

from dream_dtb.gui import Controller
# from dream_dtb.db import Connection
from dream_dtb import config
from dream_dtb import Base
from dream_dtb import Engine
from dream_dtb.util import session_scope
from dream_dtb.db import Dream
from dream_dtb.db import DreamDAO
from dream_dtb.db import Tag
from dream_dtb.db import DreamType


def launch_gui(date=None, title=None, tags=None, drtype=None):
    # TODO: add parameters to the controller so that it opens with a specified
    # dream and nvim ready to typed
    app = Controller()
    app.RunGui()


# enable -h as an help flag
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.group(context_settings=CONTEXT_SETTINGS, cls=DefaultGroup, default='add', default_if_no_args=True)
# @click.command()
# @click.option('--as-cowboy', '-c', is_flag=True, help='Greet as a cowboy.')
# @click.argument('name', default='world', required=False)
def main():
    """Dream note gui """
    # launch_gui()
    # click.echo('{0}, {1}.'.format(greet, name))
    # db_uri = 'sqlite:///{}'.format(config.DB_PATH)
    # print(db_uri)
    # app = Controller()
    # app.RunGui()
    # print("main")
    pass

    # conn = Connection(db_uri, Base)
    # print(conn.engine)
    # print(datetime.datetime.utcnow)
    # print(type(datetime.datetime.utcnow))

def test():
    # data = [Dream(title='reve1', recit='Je vais à la piscine', date=datetime.datetime.strptime('24052010', "%d%m%Y").date()), Dream(title='reve2', recit='Je vais à la plage.', date=datetime.datetime.strptime('24052010', "%d%m%Y").date())]
    data = [{'title': 'reve1', 'recit': 'je vais à la piscine', 'date':
            datetime.datetime.strptime('24052010', "%d%m%Y").date()},
            {'title': 'reve2', 'recit': 'je vais à la maison', 'date':
            datetime.datetime.strptime('25052010', "%d%m%Y").date()}]

    for elem in data:
        DreamDAO.create(elem)
    #     elem.create(conn.engine, ['bla', 'bli'], 'normal')

    with session_scope() as session:
        print("--DREAM--")
        for inst in session.query(Dream).all():
            print(inst)

        print("--DREAMTYPE--")
        for inst in session.query(DreamType).all():
            print(inst)

        print("--TAG--")
        for inst in session.query(Tag).all():
            print(inst)


@click.command(context_settings=CONTEXT_SETTINGS)
def add(**kwargs):
    """ start writing a dream """
    # print("add a dream to the database")
    # test()
    launch_gui()


@click.command(context_settings=CONTEXT_SETTINGS)
def browse(**kwargs):
    """ browse dream database """
    print("browse dreams in web navigator")


@click.command(context_settings=CONTEXT_SETTINGS)
def book(**kwargs):
    """ create a pdf from the dream database """
    print("pdf created")


@click.command(context_settings=CONTEXT_SETTINGS)
def stat(**kwargs):
    """ output some statistics about the dream database """
    print("output stats")


@click.command()
@click.pass_context
def help(ctx):
    """ Display help message """
    print(ctx.parent.get_help())


main.add_command(add)
main.add_command(browse)
main.add_command(book)
main.add_command(stat)
main.add_command(help)


if __name__ == '__main__':
    main()
