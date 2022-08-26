import asyncio
from collections import defaultdict
from io import BytesIO
from aiogram import types
from i18n import t
from pymongo import ReturnDocument
import numpy as np
import keyboards
import db
from main import AdmissionQueue
from stages import Stage
import logging
from aiogram.utils import exceptions
import prometheus
from ocr import get_code_from_image
from cv2 import cv2

logger = logging.getLogger('commands')


def alnum(x: str):
    return ''.join(ch for ch in x if ch.isalnum() or ch == ' ')


def apply_handlers(aq: AdmissionQueue):
    async def start_handler(message: types.Message):
        if message.chat.id in aq.adm_chat_ids:
            return

        prometheus.start_handler_cnt.inc({})

        user = await db.users.find_one({'uid': message.chat.id})
        if user is not None:
            if user['stage'] in [Stage.ask_faculty]:
                return
        else:
            user = db.users.insert_one({'uid': message.chat.id, 'lang': 'ua', 'stage': Stage.ask_faculty, 'page': 0,
                                        'verified': False, 'voted': False})
            await message.reply(f"{t('GREETINGS', locale='ua')}\n\n"
                                f"{t('ASK_FACULTY', locale='ua')}\n"
                                f"{t('PAGE', page=1, total=len(aq.faculties) // 8, locale='ua')}",
                                reply_markup=keyboards.get_faculties_kbd(list(aq.faculties.keys())),
                                parse_mode=types.ParseMode.HTML)

    async def query_handler(query: types.CallbackQuery):
        if query.message.chat.id in aq.adm_chat_ids:
            if query.data.startswith('IDConfirm'):
                uid, stud_id = map(int, query.data.split('IDConfirm', 1)[1].split(','))
                user = await db.users.find_one({'uid': uid})
                user_tg = await aq.bot.get_chat(uid)
                match = await db.users.find_one({'stud_id': stud_id})
                if match:
                    reply_msg = '#TODO\n'
                    match_user = await aq.bot.get_chat(match['uid'])
                    username = f'@{match_user.username}\n' if match_user.username else f'<a href="tg://user?id={match.id}">{alnum(match_user.full_name)}</a>\n'
                    reply_msg += f'Факультет: {user["faculty"]}\n'
                    reply_msg += f'⚠️⚠️⚠️ Цей студентський вже використав {username} ⚠️⚠️⚠️\n'
                    reply_msg += f'ID: {stud_id}\n'

                    reply_msg += f'@{user_tg.username}' if user_tg.username else f'<a href="tg://user?id={user_tg.id}">{alnum(user_tg.full_name)}</a>\n'
                    return await query.message.edit_caption(reply_msg, parse_mode=types.ParseMode.HTML,
                                                            reply_markup=keyboards.get_force_photo_kbd(uid, stud_id))

                reply_msg = f'#Verified\nID: {stud_id}\n'
                reply_msg += f'Факультет: {user["faculty"]}\n'
                reply_msg += f'@{user_tg.username}' if user_tg.username else f'<a href="tg://user?id={user_tg.id}">{alnum(user_tg.full_name)}</a>'

                await query.message.edit_caption(reply_msg, parse_mode=types.ParseMode.HTML)
                await aq.bot.send_message(uid, t('GO_TO_VOTING', locale=user['lang']),
                                          reply_markup=keyboards.get_start_vote_kbd(user['lang']))
                await db.users.find_one_and_update({'uid': user['uid']},
                                                   {'$set': {'verified': True, 'stage': Stage.start_votes,
                                                             'stud_id': stud_id}})

            elif query.data.startswith('IDForceConfirm'):
                uid, stud_id = map(int, query.data.split('IDForceConfirm', 1)[1].split(','))
                user = await db.users.find_one({'uid': uid})
                user_tg = await aq.bot.get_chat(uid)

                reply_msg = f'#Verified #ForceVerified\nID: {stud_id}\n'
                reply_msg += f'Факультет: {user["faculty"]}\n'
                reply_msg += f'@{user_tg.username}' if user_tg.username else f'<a href="tg://user?id={user_tg.id}">{alnum(user_tg.full_name)}</a>'

                await query.message.edit_caption(reply_msg, parse_mode=types.ParseMode.HTML)
                await aq.bot.send_message(uid, t('GO_TO_VOTING', locale=user['lang']),
                                          reply_markup=keyboards.get_start_vote_kbd(user['lang']))
                await db.users.find_one_and_update({'uid': user['uid']},
                                                   {'$set': {'verified': True, 'stage': Stage.start_votes,
                                                             'stud_id': stud_id}})

            elif query.data.startswith('IDDeny'):
                uid = int(query.data.split('IDDeny', 1)[1])
                user = await db.users.find_one({'uid': uid})
                user_tg = await aq.bot.get_chat(uid)
                reply_msg = f'#Denied\n'
                reply_msg += f'Факультет: {user["faculty"]}\n'
                reply_msg += f'@{user_tg.username}' if user_tg.username else f'<a href="tg://user?id={user_tg.id}">{alnum(user_tg.full_name)}</a>'
                await query.message.edit_caption(reply_msg, parse_mode=types.ParseMode.HTML)
                await aq.bot.send_message(uid, t('ID_NOT_ACCEPTED', locale=user['lang']))

            elif query.data.startswith('IDFacErr'):
                uid = int(query.data.split('IDFacErr', 1)[1])
                user = await db.users.find_one({'uid': uid})
                user_tg = await aq.bot.get_chat(uid)
                reply_msg = f'#Denied #WrongFaculty\n'
                reply_msg += f'Факультет: {user["faculty"]}\n'
                reply_msg += f'@{user_tg.username}' if user_tg.username else f'<a href="tg://user?id={user_tg.id}">{alnum(user_tg.full_name)}</a>'
                await query.message.edit_caption(reply_msg, parse_mode=types.ParseMode.HTML)
                await db.users.find_one_and_update({'uid': uid}, {'$set': {'stage': Stage.ask_faculty, 'page': 0, }})
                await aq.bot.send_message(uid, t('WRONG_FACULTY', locale=user['lang']) + '\n' +
                                          f"{t('PAGE', page=1, total=len(aq.faculties) // 8, locale='ua')}",
                                          reply_markup=keyboards.get_faculties_kbd(list(aq.faculties.keys())),
                                          parse_mode=types.ParseMode.HTML)

            return

        user = await db.users.find_one({'uid': query.from_user.id})
        if user is None:
            try:
                return await query.answer()
            except exceptions.InvalidQueryID:
                pass  # ignore

        elif query.data.startswith('FacultySet'):
            faculty = query.data.split('FacultySet', 1)[1]
            await db.users.find_one_and_update({'uid': user['uid']},
                                               {'$set': {'faculty': faculty, 'stage': Stage.confirm_faculty}})
            await query.answer()
            await query.message.edit_text(t('CONFIRM_FACULTY', faculty=faculty, locale=user['lang']),
                                          reply_markup=keyboards.get_faculty_confirm_kbd(lang=user['lang']))

        elif query.data.startswith('FacultyConfirm'):
            await db.users.find_one_and_update({'uid': user['uid']}, {'$set': {'stage': Stage.send_ID}})
            await query.answer()
            await query.message.edit_text(t('SEND_ID', locale=user['lang']))
            await query.message.delete_reply_markup()

        elif query.data.startswith('FacultyDeny'):
            await query.message.edit_text(f"{t('ASK_FACULTY', locale='ua')}\n"
                                          f"{t('PAGE', page=1, total=len(aq.faculties) // 8, locale='ua')}",
                                          reply_markup=keyboards.get_faculties_kbd(list(aq.faculties.keys())),
                                          parse_mode=types.ParseMode.HTML)

        elif query.data.startswith('BtnLeft') or query.data.startswith('BtnRight'):
            if user['stage'] == Stage.ask_faculty:
                max_faculty_pages = len(aq.faculties) // 8
                user['page'] += -1 if query.data.startswith('BtnLeft') else 1
                user['page'] %= max_faculty_pages

                await query.answer()
                await query.message.edit_text(f"{t('ASK_FACULTY', locale='ua')}\n"
                                              f"{t('PAGE', page=user['page'] + 1, total=len(aq.faculties) // 8, locale='ua')}",
                                              reply_markup=keyboards.get_faculties_kbd(list(aq.faculties.keys()),
                                                                                       user['page'], user['lang']),
                                              parse_mode=types.ParseMode.HTML)
                await db.users.find_one_and_update({'uid': user['uid']}, {'$set': {'page': user['page']}})

            if user['stage'] == Stage.voting:
                vote_num = aq.users_state[user["uid"]]["vote_num"]
                state = aq.users_state[user['uid']]['votes'][f'vote_{vote_num}']
                vote = aq.faculties[user['faculty']][f'vote_{vote_num}']

                state['current_candidate'] += -1 if query.data.startswith('BtnLeft') else 1
                try:
                    state['current_candidate'] %= len(vote['candidates'])
                except ZeroDivisionError:
                    logger.error('Devizion by zero at BtnLeft/Right (no candidates)')
                    state['current_candidate'] = 0
                await query.answer()
                await show_vote(user, query.message)

        elif query.data.startswith('VoteStart'):
            user = await db.users.find_one_and_update({'uid': user['uid']}, {'$set': {'stage': Stage.voting}},
                                                      return_document=ReturnDocument.AFTER)
            await query.answer()
            await show_vote(user, query.message)

        elif query.data.startswith('VoteSelect'):
            vote_num = aq.users_state[user["uid"]]["vote_num"]
            state = aq.users_state[user['uid']]['votes'][f'vote_{vote_num}']

            state['selected_candidates'].append(state['current_candidate'])
            await query.answer()
            await show_vote(user, query.message)

        elif query.data.startswith('VoteDeselect'):
            vote_num = aq.users_state[user["uid"]]["vote_num"]
            state = aq.users_state[user['uid']]['votes'][f'vote_{vote_num}']

            state['selected_candidates'].remove(state['current_candidate'])
            await query.answer()
            await show_vote(user, query.message)

        elif query.data.startswith('VoteSubmit'):
            vote_num = aq.users_state[user["uid"]]["vote_num"]
            state = aq.users_state[user['uid']]['votes'][f'vote_{vote_num}']
            candidates = aq.faculties[user['faculty']][f'vote_{vote_num}']['candidates']

            reply = f'<b>{t("VOTE" + str(vote_num + 1), faculty=user["faculty"], locale=user["lang"])}</b>\n\n' \
                    f'{t("VOTE_CONFIRMATION", locale=user["lang"])}\n\n' \
                    f'<b>'
            for c in state['selected_candidates']:
                reply += f'● {candidates[c]["name"]} - {candidates[c]["group"]}\n'
            if not state['selected_candidates']:
                reply += t('AGAINST_ALL', locale=user['lang'])
            reply += '</b>'

            await query.answer()
            await query.message.edit_text(reply, reply_markup=keyboards.get_vote_confirm_kbd(user['lang']),
                                          parse_mode=types.ParseMode.HTML)

        elif query.data.startswith('VoteEdit'):
            await query.answer()
            await show_vote(user, query.message)

        elif query.data.startswith('VoteConfirm'):
            state = aq.users_state[user["uid"]]
            if state["vote_num"] < 3:
                state["vote_num"] += 1
                await show_vote(user, query.message)
            else:
                await submit_votes(user, query.message)

            await query.answer()

        else:
            logger.warning(f'Got invalid command {query.data}')

        try:
            await query.answer()  # try to answer query if not answered already
        except exceptions.InvalidQueryID:  # already answered
            pass

    async def submit_votes(user, message: types.Message):
        state = aq.users_state[user['uid']]
        votes = aq.faculties[user['faculty']]
        user = await db.users.find_one_and_update({'uid': user['uid']}, {'$set': {'voted': True}},
                                                  return_document=ReturnDocument.BEFORE)
        reply = t('VOTED_FOR', locale=user['lang'])
        if not user['voted'] and user['verified'] and \
                all([len(state['votes'][f'vote_{vote_num}']['selected_candidates']) <= votes[f'vote_{vote_num}'][
                    'quota']
                     for vote_num in range(4)]):
            for vote_num in range(4):
                reply += f"\n{t(f'VOTE' + str(vote_num + 1), faculty=user['faculty'], locale=user['lang'])}\n"
                for candidate in state['votes'][f'vote_{vote_num}']['selected_candidates']:
                    c_profile = votes[f'vote_{vote_num}']['candidates'][candidate]
                    await db.votes.find_one_and_update({'faculty': user['faculty'], 'vote': vote_num,
                                                        'name': c_profile['name'], 'group': c_profile['group']},
                                                       {'$inc': {'votes': 1}}, upsert=True)
                    reply += f"{c_profile['name']} - {c_profile['group']}\n"
                if not state['votes'][f'vote_{vote_num}']['selected_candidates']:
                    reply += f"{t('AGAINST_ALL', locale=user['lang'])}\n"

            reply += '\n\n'

            await message.edit_text(reply + t('SUCCESSFULLY_VOTED', locale=user['lang']),
                                    parse_mode=types.ParseMode.HTML)

            state['votes'].clear()  # clear in-memory array of candidates voted for by this user
        else:
            logger.warning('Attempt to submit_votes while not verified/already voted/invalid quotas')
            logger.warning(user)
            pass

    async def show_vote(user, message: types.Message):
        vote_num = aq.users_state[user['uid']]['vote_num']
        state = aq.users_state[user['uid']]['votes'][f'vote_{vote_num}']
        resp = t(f'VOTE{vote_num + 1}', faculty=user['faculty'], locale=user['lang']) + '\n\n'
        resp += t('VOTE_HOWTO', locale=user['lang']) + '\n\n'
        vote = aq.faculties[user['faculty']][f'vote_{vote_num}']
        is_selected = state['current_candidate'] in state['selected_candidates']
        for num, c in enumerate(vote['candidates']):
            if num == state['current_candidate']:
                resp += '<b>➡️'

            if num in state['selected_candidates']:
                resp += f'✅ {c["name"]} - {c["group"]}'
            else:
                resp += f'●   {c["name"]} - {c["group"]}'

            if num == state['current_candidate']:
                resp += '</b>'

            resp += '\n'

        resp += f'\n{t("VOTE_CNT", num=len(state["selected_candidates"]), total=min(vote["quota"], len(vote["candidates"])))}'

        is_maxed_out = len(state['selected_candidates']) == vote['quota']
        is_zero = len(state['selected_candidates']) == 0

        if len(vote['candidates']) == 0:
            return await message.edit_text(t(f'VOTE{vote_num + 1}', faculty=user['faculty'], locale=user['lang'])
                                           + '\n\n' + t('NO_CANDIDATES', locale=user['lang']),
                                           reply_markup=keyboards.get_vote_skip_kbd(user['lang']),
                                           parse_mode=types.ParseMode.HTML)
        await message.edit_text(resp,
                                reply_markup=keyboards.get_vote_kbd(is_selected, is_maxed_out, is_zero, user['lang']),
                                parse_mode=types.ParseMode.HTML)

    async def photo_handler(message: types.Message):
        user = await db.users.find_one({'uid': message.from_user.id})
        if user is None:
            return await start_handler(message)

        if user['stage'] == Stage.send_ID:
            photo = BytesIO()
            await message.photo[-1].download(destination_file=photo)
            file_bytes = np.asarray(bytearray(photo.read()), dtype=np.uint8)
            img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

            photo.seek(0)
            code = get_code_from_image(img)

            reply_msg = ''

            if code:
                code = int(code)
                match = await db.users.find_one({'stud_id': code})
                if match:
                    match_user = await aq.bot.get_chat(match['uid'])
                    username = f'@{match_user.username}\n' if match_user.username else f'<a href="tg://user?id={match.id}">{alnum(match_user.full_name)}</a>\n'
                    reply_msg += f'\n⚠️⚠️⚠️ Цей студентський вже використав {username} ⚠️⚠️⚠️\n'
                reply_msg += f'ID: {code}\n'

            if not reply_msg:
                reply_msg = 'Реплайніть на це повідомлення ID студентського\n'

            reply_msg += '#TODO\n'
            reply_msg += f'Факультет: {user["faculty"]}\n'
            reply_msg += f'@{message.from_user.username}' if message.from_user.username else f'<a href="tg://user?id={user["uid"]}">{alnum(message.from_user.full_name)}</a>\n'
            await message.bot.send_photo(chat_id=aq.faculties[user['faculty']]['adm_chat_id'],
                                         photo=photo, caption=reply_msg,
                                         parse_mode=types.ParseMode.HTML,
                                         reply_markup=keyboards.get_photo_kbd(user['uid'], code, lang=user['lang']))
            await message.reply(t('WAIT_FOR_VERIFICATION', locale=user['lang']))

    async def text_handler(message: types.Message):
        if message.chat.id in aq.adm_chat_ids:
            if message.reply_to_message and message.reply_to_message.from_user.id == aq.bot.id:
                reply = message.reply_to_message
                if not message.text.isnumeric():
                    return await message.reply('Будь ласка, використовуйте тільки цифри')
                stud_id = int(message.text)
                uid = int(list(reply.reply_markup.iter_values())[0][-1][0]['callback_data'].split('IDDeny', 1)[1])
                user = await db.users.find_one({'uid': uid})
                user_tg = await aq.bot.get_chat(uid)
                match = await db.users.find_one({'stud_id': stud_id})
                if match:
                    reply_msg = '#TODO\n'
                    match_user = await aq.bot.get_chat(match['uid'])
                    username = f'@{match_user.username}\n' if match_user.username else f'<a href="tg://user?id={match.id}">{alnum(match_user.full_name)}</a>\n'
                    reply_msg += f'Факультет: {user["faculty"]}\n'
                    reply_msg += f'⚠️⚠️⚠️ Цей студентський вже використав {username} ⚠️⚠️⚠️\n'
                    reply_msg += f'ID: {stud_id}\n'

                    reply_msg += f'@{user_tg.username}' if user_tg.username else f'<a href="tg://user?id={user_tg.id}">{alnum(user_tg.full_name)}</a>\n'
                    return await message.reply_to_message.edit_caption(reply_msg, parse_mode=types.ParseMode.HTML,
                                                                       reply_markup=keyboards.get_force_photo_kbd(uid,
                                                                                                                  stud_id))

                reply_msg = f'#TODO\nID: {stud_id}\n'
                reply_msg += f'Факультет: {user["faculty"]}\n'
                reply_msg += f'@{user_tg.username}' if user_tg.username else f'<a href="tg://user?id={user_tg.id}">{alnum(user_tg.full_name)}</a>'

                await message.reply_to_message.edit_caption(reply_msg, parse_mode=types.ParseMode.HTML,
                                                            reply_markup=keyboards.get_photo_kbd(user['uid'], stud_id,
                                                                                                 lang=user['lang']))
                # await aq.bot.send_message(uid, t('GO_TO_VOTING', locale=user['lang']),
                #                           reply_markup=keyboards.get_start_vote_kbd(user['lang']))
                # await db.users.find_one_and_update({'uid': user['uid']},
                #                                    {'$set': {'verified': True, 'stage': Stage.start_votes,
                #                                              'stud_id': stud_id}})

    async def calc_handler(message: types.Message):
        if message.chat.id in aq.bot_admins:
            res = defaultdict(lambda: '')
            for faculty in aq.faculties:
                for vote_num in range(4):
                    cur = db.votes.find({'faculty': faculty, 'vote': vote_num})
                    cur.sort('votes', -1).limit(aq.faculties[faculty][f'vote_{vote_num}']['quota'])
                    line = t(f'VOTE{vote_num + 1}_NONUM', faculty=faculty) + '\n'
                    async for doc in cur:
                        line += f'{doc["name"]} - {doc["votes"]} голосів\n'
                    res[faculty] += line + '\n'

            for faculty in aq.faculties:
                await aq.bot.send_message(aq.faculties[faculty]['adm_chat_id'],
                                          'Результати голосувань:\n' + res[faculty], parse_mode=types.ParseMode.HTML)
                await asyncio.sleep(0.1)

            users = db.users.find({'faculty': {'$exists': True}})
            async for user in users:
                await aq.bot.send_message(user['uid'], 'Результати голосувань:\n' + res[user['faculty']],
                                          parse_mode=types.ParseMode.HTML)
                await asyncio.sleep(0.1)

            reply = ''
            for faculty in aq.faculties:
                reply += f'<b><i>{faculty}</i></b>\n\n'
                reply += res[faculty]
            reply_bytes = BytesIO()
            reply_bytes.write(reply.encode())
            reply_bytes.seek(0)
            file = types.InputFile(reply_bytes, 'result.txt')
            await message.reply_document(reply_bytes)

    handlers = [
        {'fun': start_handler, 'named': {'commands': ['start']}},
        {'fun': calc_handler, 'named': {'commands': ['calc']}},
        {'fun': photo_handler, 'named': {'content_types': types.ContentType.PHOTO}},
        {'fun': text_handler, 'named': {'content_types': types.ContentType.TEXT}}
    ]

    for handler in handlers:
        aq.dp.register_message_handler(handler['fun'], **handler['named'])
    aq.dp.register_callback_query_handler(query_handler)
