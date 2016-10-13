import asyncio

import telepot
import telepot.aio

from config import config
from markoviser import (HTTPRequestErrorException, Markoviser,
                        MarkovGeneratorErrorException)
import utils


class TelegramBotException(Exception):
    pass


class TelegramBot(telepot.aio.Bot):
    HELP_MESSAGE = ("Just input anything and I'll generate some random text " +
                    'using it as a basis.')
    INVALID_CMD = ("I don't know what you mean by that. If you need help, " +
                   'use /help.')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._answerer = telepot.aio.helper.Answerer(self)

    async def on_chat_message(self, message):
        try:
            content_type, chat_type, chat_id = telepot.glance(message)

            # ignore this message if it is not text
            if content_type != 'text':
                return

            name = self.format_name(message)
            longname = '{chat_id} ({name})'.format(chat_id=chat_id,
                                                   name=name)
            utils.logging.info(('Message from {longname}: "{message_text}"')
                               .format(longname=longname,
                                       message_text=message['text']))

            if message['text'].startswith('/'):
                command = message['text'].split(' ')[0][1:]
                if command == 'help':
                    _msg = self.HELP_MESSAGE
                elif command == 'start':
                    _msg = self.HELP_MESSAGE
                else:
                    _msg = self.INVALID_CMD
                await self.send_message(message, _msg, no_preview=True)
                return

            # check rate limit
            if chat_id not in config['telegram']['rate_limit_exempt_chat_ids']:
                rate_limit = utils.rate_limit.hit('telegram', chat_id)
                if not rate_limit['allowed']:
                    _msg = (('Message from {longname}: throttled ' +
                            '(resets in {reset} seconds)')
                            .format(longname=longname,
                                    reset=rate_limit['reset']))
                    utils.logging.warn(_msg)
                    _msg = (('Not so fast! Try again in {}.')
                            .format(utils.timedelta(rate_limit['reset'])))
                    await self.send_message(message, _msg)
                    return

            text = message['text'].strip().strip('\n')
            try:
                m = Markoviser.from_text(text)
            except HTTPRequestErrorException:
                result = "I can't access that URL."
            except MarkovGeneratorErrorException:
                result = ("There isn't enough text there for me to generate " +
                          'a proper shitpost for you.')
            else:
                result = m.spam

            await self.send_message(message, result)
        except Exception as e:
            utils.logging.exception('Error handling {longname} ({type})'
                                    .format(longname=longname,
                                            type=message['chat']['type']))
            await self.send_message(message, 'Sorry, try again.')

    async def send_message(self, message, caption, filename=None,
                           no_preview=False):
        if filename:
            caption = utils.ellipsis(caption, 200)
            with open(filename, 'rb') as f:
                await self.sendPhoto(message['chat']['id'],
                                     f, caption=caption)
        else:
            caption = utils.ellipsis(caption, 4096)
            await self.sendMessage(message['chat']['id'],
                                   caption,
                                   disable_web_page_preview=no_preview)

    def format_name(self, message):
        longname = []
        if 'username' in message['from']:
            longname.append('@' + message['from']['username'])
        if 'first_name' in message['from']:
            longname.append(message['from']['first_name'])
        if 'last_name' in message['from']:
            longname.append(message['from']['last_name'])
        return ', '.join(longname)


if __name__ == '__main__':
    bot = TelegramBot(config['telegram']['token'])

    loop = asyncio.get_event_loop()
    loop.create_task(bot.message_loop())

    try:
        loop.run_forever()
    finally:
        loop.close()
