import click
from datetime import datetime
from click_default_group import DefaultGroup
from click_datetime import Datetime
import logging
import logging.config


from dream_dtb.gui import Controller
from dream_dtb import config

logging.config.dictConfig(config.LOGGING)
logger = logging.getLogger('dream_logger')


def launch_gui(instance=None):
    """ wrapper to launch the main gtk window
    if instance is not None, nvim will start with a dream open
    """
    app = Controller(instance)
    app.RunGui()


# enable -h as an help flag
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.group(context_settings=CONTEXT_SETTINGS, cls=DefaultGroup, default='launch', default_if_no_args=True)
def main():
    """Dream note gui """
    pass


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option('--date', type=Datetime(format='%Y-%m-%d'),
              default=datetime.now(),
              help='date of dream YYYY-MM-DD, default to today')
@click.option('--type', type=str, default='normal',
              help='dream type (normal, lucid, ...) default to normal')
@click.option('--tags', '-t', type=str, default=None, multiple=True,
              help='tags of the dream. Can be specified multiple times')
@click.argument('title')
def add(**kwargs):
    """ Add a new dream """
    logger.info('add dream command')
    instance = {}
    instance['date'] = kwargs['date'].date()
    instance['tags'] = list(kwargs['tags'])
    instance['drtype'] = kwargs['type']
    instance['title'] = kwargs['title']
    launch_gui(instance)


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


@click.command(context_settings=CONTEXT_SETTINGS)
def launch(**kwargs):
    """ Start the gui (same as dreamdtb without any subcommand) """
    logger.info('launch dream command')
    launch_gui()


@click.command()
@click.pass_context
def help(ctx):
    """ Display help message """
    print(ctx.parent.get_help())


main.add_command(add)
main.add_command(browse)
main.add_command(book)
main.add_command(launch)
main.add_command(stat)
main.add_command(help)


if __name__ == '__main__':
    main()
