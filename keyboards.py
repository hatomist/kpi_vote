from aiogram import types
from i18n import t


def divide_chunks(a, n):
    for i in range(0, len(a), n):
        yield a[i:i + n]


def get_faculties_kbd(faculties_list, page_num=0, lang='ua'):
    kbd = list(
        types.InlineKeyboardButton(faculty, callback_data=f'FacultySet{faculty}')
        for faculty in faculties_list[8 * page_num:8 * (page_num + 1)]
    )

    return types.InlineKeyboardMarkup(
        row_width=2,
        inline_keyboard=list(divide_chunks(kbd, 2)) +
            [
                [types.InlineKeyboardButton(t('BTN_LEFT', locale=lang), callback_data='BtnLeft'),
                 types.InlineKeyboardButton(t('BTN_RIGHT', locale=lang), callback_data='BtnRight')]
            ]
    )


def get_faculty_confirm_kbd(lang='ua'):
    return types.InlineKeyboardMarkup(
        row_width=2,
        inline_keyboard=(
            (
                types.InlineKeyboardButton(t('BTN_CONFIRM', locale=lang), callback_data='FacultyConfirm'),
            ),
            (
                types.InlineKeyboardButton(t('BTN_EDIT', locale=lang), callback_data='FacultyDeny'),
            ),
        )
    )


def get_start_vote_kbd(lang='ua'):
    return types.InlineKeyboardMarkup(
        row_width=2,
        inline_keyboard=(
            (
                types.InlineKeyboardButton(t('BTN_START_VOTE', locale=lang), callback_data='VoteStart'),
            ),
        )
    )


def get_vote_skip_kbd(lang='ua'):
    return types.InlineKeyboardMarkup(
        row_width=2,
        inline_keyboard=[[types.InlineKeyboardButton(t('BTN_SKIP_VOTE', locale=lang), callback_data='VoteSubmit')]]
    )


def get_vote_kbd(is_selected, is_maxed_out, is_zero, lang='ua'):
    kbd = [
        [
            types.InlineKeyboardButton(t('BTN_LEFT', locale=lang), callback_data='BtnLeft'),
             types.InlineKeyboardButton(t('BTN_RIGHT', locale=lang), callback_data='BtnRight')]
    ]

    if is_maxed_out:
        if is_selected:
            kbd.append([types.InlineKeyboardButton(t('BTN_DESELECT', locale=lang), callback_data='VoteDeselect')])

    else:
        if is_selected:
            kbd.append([types.InlineKeyboardButton(t('BTN_DESELECT', locale=lang), callback_data='VoteDeselect')])
        else:
            kbd.append([types.InlineKeyboardButton(t('BTN_SELECT', locale=lang), callback_data='VoteSelect')])

    if is_zero:
        kbd.append([types.InlineKeyboardButton(t('BTN_AGAINST_ALL', locale=lang), callback_data='VoteSubmit')])
    else:
        kbd.append([types.InlineKeyboardButton(t('BTN_SUBMIT', locale=lang), callback_data='VoteSubmit')])

    return types.InlineKeyboardMarkup(
        row_width=2,
        inline_keyboard=kbd
    )


def get_vote_confirm_kbd(lang='ua'):
    return types.InlineKeyboardMarkup(
        row_width=2,
        inline_keyboard=(
            (
                types.InlineKeyboardButton(t('BTN_CONFIRM', locale=lang), callback_data='VoteConfirm'),
            ),
            (
                types.InlineKeyboardButton(t('BTN_EDIT', locale=lang), callback_data='VoteEdit'),
            ),
        )
    )


def get_photo_kbd(uid, code, lang='ua'):
    if code:
        return types.InlineKeyboardMarkup(
            row_width=2,
            inline_keyboard=(
                (
                    types.InlineKeyboardButton(t('BTN_CONFIRM', locale=lang), callback_data=f'IDConfirm{uid},{code}'),
                ),
                (
                    types.InlineKeyboardButton(t('BTN_WRONG_FACULTY', locale=lang), callback_data=f'IDFacErr{uid}'),
                ),
                (
                    types.InlineKeyboardButton(t('BTN_DENY', locale=lang), callback_data=f'IDDeny{uid}'),
                ),
            )
        )
    else:
        return types.InlineKeyboardMarkup(
            row_width=2,
            inline_keyboard=(
                (
                    types.InlineKeyboardButton(t('BTN_WRONG_FACULTY', locale=lang), callback_data=f'IDFacErr{uid}'),
                ),
                (
                    types.InlineKeyboardButton(t('BTN_DENY', locale=lang), callback_data=f'IDDeny{uid}'),
                ),
            )
        )


def get_force_photo_kbd(uid, code, lang='ua'):
    return types.InlineKeyboardMarkup(
        row_width=2,
        inline_keyboard=(
            (
                types.InlineKeyboardButton(t('BTN_FORCE_CONFIRM', locale=lang), callback_data=f'IDForceConfirm{uid},{code}'),
            ),
            (
                types.InlineKeyboardButton(t('BTN_DENY', locale=lang), callback_data=f'IDDeny{uid}'),
            ),
        )
    )
