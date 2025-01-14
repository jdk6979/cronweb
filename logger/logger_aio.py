import os
import functools
import typing
import pathlib
import asyncio
import datetime
import aiofile
import logger
import cronweb


class AioLogger(logger.LoggerBase):
    def __init__(self, log_dir: typing.Union[str, pathlib.Path],
                 controller: typing.Optional[cronweb.CronWeb] = None):
        super().__init__(controller)
        self.log_dir = pathlib.Path(log_dir)
        self.task_dict: typing.Dict[str, asyncio.Task] = {}
        if not self.log_dir.exists():
            self.log_dir.mkdir(parents=True)

    def get_log_queue(self, uuid: str, shot_id: str) -> typing.Tuple[asyncio.queues.Queue, pathlib.Path]:
        self._py_logger.debug('获取执行日志通道 uuid:%s', uuid)
        queue = asyncio.Queue()
        now = datetime.datetime.now()
        file_name = f'{int(now.timestamp() * 1000)}-{shot_id}.log'
        path_log_file = self.log_dir / file_name
        task = asyncio.create_task(self._log_recording(queue, path_log_file, now))
        task.add_done_callback(functools.partial(self._log_recording_cb, self.task_dict, file_name))
        self.task_dict[file_name] = task
        return queue, path_log_file

    async def read_log_by_path(self, log_path: typing.Union[str, pathlib.Path],
                               limit_line: int = 1000) -> typing.Optional[str]:
        """根据path读取文件"""
        log_path = pathlib.Path(log_path)
        if not log_path.exists() or log_path.is_dir():
            self._py_logger.error('log文件不存在 %s', log_path)
            return None
        self._py_logger.debug('打开log文件 %s', log_path)
        async with aiofile.async_open(str(log_path), 'r', encoding='utf8 ') as afp:
            # aiofile的readline对utf8字符有兼容性问题
            raw: str = await afp.read()
            lines = raw.splitlines(keepends=True)
            if len(lines) > limit_line:
                lines = lines[:limit_line]
        return ''.join(lines)

    def remove_log_file(self, log_path: typing.Union[str, pathlib.Path]) -> typing.Optional[pathlib.Path]:
        """根据path删除文件"""
        log_path = pathlib.Path(log_path)
        if not log_path.exists() or log_path.is_dir():
            return None
        os.remove(log_path)
        return log_path

    def get_all_log_file_path(self) -> typing.List[pathlib.Path]:
        """获取所有日志文件的Path对象列表"""
        return list(self.log_dir.glob('*.log'))

    @staticmethod
    def _log_recording_cb(task_dict: typing.Dict[str, asyncio.Task], file_name: str,
                          task: asyncio.Task):
        task_dict.pop(file_name)

    @staticmethod
    async def _log_recording(queue: asyncio.queues.Queue,
                             path_log_file: typing.Union[str, pathlib.Path],
                             now: datetime.datetime) -> None:
        async with aiofile.async_open(str(path_log_file), 'w', encoding='utf8') as afp:
            await afp.write(f'{now}\n')
            while True:
                try:
                    line = await asyncio.wait_for(queue.get(), timeout=1800)
                except asyncio.TimeoutError:
                    break
                if line is logger.LogStop:
                    break
                await afp.write(line)
            await afp.write(f'\n{datetime.datetime.now()}')

        return None
