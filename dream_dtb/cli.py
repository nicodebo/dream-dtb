import click
from click_default_group import DefaultGroup
import logging
import logging.config

from dream_dtb.gui import Controller
from dream_dtb import config

logging.config.dictConfig(config.LOGGING)
logger = logging.getLogger('dream_logger')


def launch_gui(date=None, title=None, tags=None, drtype=None):
    app = Controller()
    app.RunGui()


# enable -h as an help flag
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.group(context_settings=CONTEXT_SETTINGS, cls=DefaultGroup, default='add', default_if_no_args=True)
def main():
    """Dream note gui """
    pass


@click.command(context_settings=CONTEXT_SETTINGS)
def add(**kwargs):
    """ start writing a dream """
    logger.info('add dream command')
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
