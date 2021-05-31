import web
import uvicorn
import fastapi
import pydantic
import cronweb
import typing


class WebFastAPI(web.WebBase):
    def __init__(self, controller: typing.Optional[cronweb.CronWeb] = None,
                 fa_kwargs: typing.Optional[typing.Dict[str, typing.Any]] = None):
        super().__init__(controller)
        fa_kwargs = fa_kwargs if fa_kwargs else {}
        self.app = fastapi.FastAPI(**fa_kwargs)
        self.init_api()

    def init_api(self):
        self._py_logger.info('初始化fastAPI路由')

        # @self.app.get('/')
        # async def index():
        #     return {'response': 'hello'}

        @self.app.get('/code')
        async def code_exp():
            return {
                '0': '成功',
                '-1': '未授权，请登录',
                '1': '执行失败，查看后台日志',
                '2': '执行失败，查看response'
            }

        class JobInfo(pydantic.BaseModel):
            cron_exp: str
            command: str
            name: str
            param: str = ''

        @self.app.post('/job')
        async def add_job(job_info: JobInfo):
            if not self._core.cron_is_valid(job_info.cron_exp):
                return {'response': 'cron表达式无效', 'code': 2}
            job = await self._core.add_job(job_info.cron_exp, job_info.command,
                                           job_info.param, name=job_info.name)
            if not job:
                return {'response': 'failed', 'code': 1}
            return {'response': 'success', 'code': 0}

        @self.app.delete('/job/{uuid}')
        async def remove_job(uuid: str):
            job = await self._core.remove_job(uuid)
            if not job:
                return {'response': 'uuid不存在', 'code': 2}
            return {'response': '删除成功', 'code': 0}

        @self.app.get('/jobs')
        async def get_all_jobs():
            """
            {
              "response": [
                {
                  "uuid": "ee5141b095d0426dbd3b375aa00de533",
                  "cron_exp": "*/1 * * * *",
                  "command": "python -c \"import time;time.sleep(30);print('done')\"",
                  "param": "",
                  "name": "睡眠",
                  "date_create": "2021-06-01 00:46:39.090237",
                  "date_update": "2021-06-01 00:46:39.090237"
                }
              ],
              "code": 0
            }
            """
            try:
                jobs = await self._core.get_jobs()
                return {'response': [job._asdict() for job in jobs.values()], 'code': 0}
            except Exception as e:
                self._py_logger.exception(e)
                return {'response': str(e), 'code': 2}

        @self.app.get('/running_jobs')
        async def get_all_running_jobs():
            """
            {
              "response": [
                {
                  "shot_id": "acd9575dc42347659c63b4940105b590",
                  "uuid": "ee5141b095d0426dbd3b375aa00de533",
                  "date_start": "2021-06-01 01:18:00.014662"
                }
              ],
              "code": 0
            }
            """
            job_shots = self._core.get_all_running_jobs()
            return {'response': [{'shot_id': shot_id, 'uuid': uuid, 'date_start': date_start}
                                 for shot_id, (uuid, date_start) in job_shots.items()], 'code': 0}

        # @self.app.delete('/running_jobs/{shot_id}')
        # async def stop_running_by_shot_id(shot_id: str):
        #     result = self._core.stop_running_by_shot_id(shot_id)
        #     if not result:
        #         return {'response': '此shot_id未在运行', 'code': 2}
        #     return {'response': '成功', 'code': 0}

        @self.app.get('/job/{uuid}/logs')
        async def get_logs_record_by_uuid(uuid: str):
            """
            {
            "response": [
                {
                  "shot_id": "676389e11bf04195a8c4ac3537b640ac",
                  "uuid": "ee5141b095d0426dbd3b375aa00de533",
                  "state": "DONE",
                  "log_path": "logs\\1622479620020-676389e11bf04195a8c4ac3537b640ac.log",
                  "date_start": "2021-06-01 00:47:00.020000",
                  "date_end": "2021-06-01 00:47:30.067080"
                }
              ],
              "code": 0
            }
            """
            records = await self._core.job_logs_get_by_uuid(uuid)
            return {'response': [rec._asdict() for rec in records], 'code': 0}

        @self.app.get('/log/{shot_id}', response_class=fastapi.responses.PlainTextResponse)
        async def get_log_by_shot_id(shot_id: str):
            log_record = await self._core.job_log_get_by_shot_id(shot_id)
            if not log_record:
                return '日志不存在'
            return log_record

    def on_shutdown(self, func: typing.Callable):
        self._py_logger.info('添加fastAPI shutdown回调')
        self.app.on_event('shutdown')(func)

    async def start_server(self, host: str = '127.0.0.1', port: int = 8000, **kwargs):
        config = uvicorn.Config(self.app, host, port, workers=1, **kwargs)
        server = uvicorn.Server(config)
        return await server.serve()
