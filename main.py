import asyncio
import logging
import os
from collections import defaultdict
from os import getcwd, path
from aiohttp import web
import commands
from aiogram import Bot, Dispatcher, executor, types
import i18n
import csv
from SafeBot import SafeBot
from urllib.parse import parse_qs
from aioprometheus import render, Registry
import prometheus
from timer import Timer


class AdmissionQueue:
    def __init__(self):
        # Logging setup
        logging.basicConfig(level=os.environ['LOGLEVEL'] if 'LOGLEVEL' in os.environ else logging.WARNING, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        logging.getLogger('aiohttp.access').setLevel(logging.WARNING)

        # Bot setup
        try:
            self.bot = SafeBot(token=os.environ['BOT_TOKEN'])
            Bot.set_current(self.bot)  # just to be sure with all of that class override things
        except KeyError:
            logging.critical('Please specify BOT_TOKEN ENV variable')
            exit(-1)
        self.dp = Dispatcher(self.bot)
        commands.apply_handlers(self)

        self.adm_chat_ids = []

        # i18n setup

        cwd = getcwd()
        translations_dir = path.abspath(path.join(cwd, 'translations'))
        if not path.isdir(translations_dir):
            logging.error(f"i18n: Translations path ({translations_dir}) does not exist")
            exit(-1)

        i18n.load_path.append(translations_dir)
        i18n.set('filename_format', '{locale}.{format}')
        i18n.set('locale', 'ua')
        i18n.set('fallback', 'ua')

        webapp = web.Application()

        # Prometheus setup
        self._prometheus_registry = Registry()
        self._prometheus_registry.register(prometheus.bot_requests_cnt)
        self._prometheus_registry.register(prometheus.user_registrations_cnt)
        self._prometheus_registry.register(prometheus.user_full_registrations_cnt)
        self._prometheus_registry.register(prometheus.queue_registrations_cnt)
        self._prometheus_registry.register(prometheus.get_my_queue_cnt)
        self._prometheus_registry.register(prometheus.geo_sent_cnt)
        self._prometheus_registry.register(prometheus.help_btn_cnt)
        self._prometheus_registry.register(prometheus.start_handler_cnt)
        self._prometheus_registry.register(prometheus.api_requests_cnt)

        prometheus.bot_requests_cnt.set({}, 0)
        prometheus.user_registrations_cnt.set({}, 0)
        prometheus.user_full_registrations_cnt.set({}, 0)
        prometheus.queue_registrations_cnt.set({}, 0)
        prometheus.get_my_queue_cnt.set({}, 0)
        prometheus.geo_sent_cnt.set({}, 0)
        prometheus.help_btn_cnt.set({}, 0)
        prometheus.start_handler_cnt.set({}, 0)
        prometheus.api_requests_cnt.set({}, 0)

        async def metrics_handler(request: web.Request):
            content, headers = render(self._prometheus_registry, [request.headers.get('accept')])
            return web.Response(body=content, headers=headers)

        webapp.router.add_get('/metrics', metrics_handler)

        # Run web server
        self.webapp = webapp

        # initialize state
        self.faculties = {}

        self.bot_admins = [364702722]

        with open('data/quotas.csv', 'r') as quotas:
            quotas.readline()
            r = csv.reader(quotas, delimiter=',')
            for row in r:
                self.faculties[row[0].strip()] = {'vote_0':  {'quota': int(row[1]), 'candidates': []},
                                                  'vote_1': {'quota': int(row[2]), 'candidates': []},
                                                  'vote_2': {'quota': int(row[3]), 'candidates': []},
                                                  'vote_3': {'quota': int(row[4]), 'candidates': []},
                                                  'adm_chat_id': int(row[5])}
                self.adm_chat_ids.append(int(row[5]))

        with open('data/candidates.csv', 'r') as candidates:
            candidates.readline()
            r = csv.reader(candidates, delimiter=',')
            for row in r:
                mapping = {'КТК факультету/інституту': 'vote_0',
                           'КТК КПІ': 'vote_1',
                           'ВР факультету/інституту': 'vote_2',
                           'ВР КПІ': 'vote_3'}
                self.faculties[row[0].strip()][mapping[row[3].strip()]]['candidates'].append(
                    {
                        'name': row[1].strip(),
                        'group': row[2].strip(),
                        'votes': 0
                    }
                )

        for faculty in self.faculties:
            for vote in self.faculties[faculty]:
                self.faculties[faculty][vote]['candidates'].sort(key=lambda x: x['name'])

        self.users_state = defaultdict(lambda:
                                       {'vote_num': 0, 'votes': {
                                           'vote_0': {'selected_candidates': [], 'current_candidate': 0},
                                           'vote_1': {'selected_candidates': [], 'current_candidate': 0},
                                           'vote_2': {'selected_candidates': [], 'current_candidate': 0},
                                           'vote_3': {'selected_candidates': [], 'current_candidate': 0},
                                       }})


if __name__ == '__main__':
    aq = AdmissionQueue()

    if 'WEBHOOK_HOST' in os.environ:
        host = os.environ['WEBHOOK_HOST']
        port = os.environ['WEBHOOK_PORT'] if 'WEBHOOK_PORT' in os.environ else 443

        async def on_startup(dp):
            await aq.bot.set_webhook(host)

        async def on_shutdown(dp):
            await aq.bot.delete_webhook()

        e = executor.set_webhook(aq.dp,
                                 webhook_path='/webhook',
                                 on_startup=on_startup,
                                 on_shutdown=on_shutdown,
                                 web_app=aq.webapp)

        e.run_app(host='localhost', port=port)

    else:
        executor.start_polling(aq.dp, skip_updates=True)
