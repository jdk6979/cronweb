# CronWeb and CronWeb-front
# Copyright (C) 2021. Sonic Young.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
import asyncio
import pathlib
import argparse
import cronweb
import logger.logger_aio
import storage.storage_aiosqlite
import trigger.trigger_aiocron
import web.web_fastapi
import worker.worker_aiosubprocess
import logging
import logging.config
import yaml
import typing


def load_config(path_config: typing.Optional[typing.Union[str, pathlib.Path]] = None) -> typing.Dict[str, typing.Any]:
    path_config = pathlib.Path(path_config) if path_config else pathlib.Path(__file__).parent / 'config.yaml'
    if not path_config.exists():
        raise IOError(f'配置文件{path_config}不存在')
    with open(path_config, 'r', encoding='utf8') as fp:
        config = yaml.load(fp, Loader=yaml.SafeLoader)
        return config


async def init(config: typing.Dict[str, typing.Any]) -> cronweb.CronWeb:
    logging.config.dictConfig(config['pylogger'])

    core = cronweb.CronWeb()
    logger_core = logger.logger_aio.AioLogger(controller=core, **config['logger'])
    trigger_core = trigger.trigger_aiocron.TriggerAioCron(controller=core)
    web_core = web.web_fastapi.WebFastAPI(controller=core, **config['web'])
    worker_core = worker.worker_aiosubprocess.AioSubprocessWorker(controller=core)
    storage_core = await storage.storage_aiosqlite.AioSqliteStorage.create(**config['storage'])
    core.set_web_default(web_core).set_worker_default(worker_core). \
        set_trigger_default(trigger_core).set_log_default(logger_core). \
        set_storage(storage_core)
    return core


async def main(path_config: typing.Optional[typing.Union[str, pathlib.Path]] = None):
    config = load_config(path_config)
    core = await init(config)
    await core.run()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='CronWeb操作工具')
    parser.add_argument('command', type=str, help='启动CronWeb',
                        choices=['run']
                        )
    parser.add_argument('-c', '--config', dest='path_config', default=[None], nargs=1, help='指定配置文件路径')
    args = parser.parse_args()

    if args.command == 'run':
        asyncio.run(main(args.path_config[0]))
