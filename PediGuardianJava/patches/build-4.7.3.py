from pathlib import Path

ROOT = Path('source/src/main/java/ir/pedirany/guardian')


def edit(rel, replacements):
    path = ROOT / rel
    text = path.read_text(encoding='utf-8')
    for old, new in replacements:
        if old not in text:
            raise SystemExit(f'Patch anchor not found in {path}: {old[:80]!r}')
        text = text.replace(old, new, 1)
    path.write_text(text, encoding='utf-8')

edit('voice/VoiceOrderQueue.java', [
    ('int n=Math.max(1,Math.min(20,count));', 'int n=Math.max(1,Math.min(200,count));'),
    ('        if(out.statusCode()<200||out.statusCode()>=300)throw new IllegalStateException("voice queue HTTP "+out.statusCode()+": "+out.body());',
     '        if(out.statusCode()==409)throw new ActiveVoiceRequestException();\n        if(out.statusCode()<200||out.statusCode()>=300)throw new IllegalStateException("voice queue HTTP "+out.statusCode()+": "+out.body());'),
    ('    private static String env(String k,String d)',
     '    public static final class ActiveVoiceRequestException extends Exception {\n'
     '        private static final long serialVersionUID = 1L;\n'
     '        public ActiveVoiceRequestException(){super("A voice-wheel request is already active for this group");}\n'
     '    }\n'
     '    private static String env(String k,String d)'),
])

edit('commands/handlers/FeatureHandler.java', [
    ('        if(n<1||n>20){c.api().sendMessage(c.chatId(),"استفاده: /voiceorder 1..20");return;}\n'
     '        if(!q.configured()){c.api().sendMessage(c.chatId(),"⚠️ Voice worker queue پیکربندی نشده است.");return;}\n'
     '        q.request(c.chatId(),c.userId(),n); c.store().audit(c.chatId(),c.userId(),"VOICE_ORDER","current_roster count="+n);\n'
     '        c.api().sendMessage(c.chatId(),"🎙️ همین الآن افراد حاضر در ویس‌کال خوانده می‌شوند و حداکثر "+n+" نفر به‌صورت تصادفی برای نوبت انتخاب می‌شوند.");',
     '        if(n<1||n>200){c.api().sendMessage(c.chatId(),"استفاده: /voiceorder 1..200");return;}\n'
     '        if(!q.configured()){c.api().sendMessage(c.chatId(),"⚠️ Voice worker queue پیکربندی نشده است.");return;}\n'
     '        try {\n'
     '            q.request(c.chatId(),c.userId(),n);\n'
     '            c.store().audit(c.chatId(),c.userId(),"VOICE_ORDER","current_roster count="+n);\n'
     '            c.api().sendMessage(c.chatId(),"🎙️ درخواست ثبت شد؛ افراد حاضر در ویس‌کال در لحظه اجرا خوانده می‌شوند و حداکثر "+n+" نفر انتخاب خواهند شد.");\n'
     '        } catch(VoiceOrderQueue.ActiveVoiceRequestException active) {\n'
     '            c.api().sendMessage(c.chatId(),"⏳ برای این گروه یک گردونه در حال پردازش است. پس از پایان آن دوباره تلاش کنید.");\n'
     '        }'),
])

edit('commands/CommandRouter.java', [
    ('if("a:wheel".equals(d)){FeatureHandler.voiceOrder(voiceOrder).handle(new CommandContext(api,store,sec,cid,user,mid,"/wheel 1",Map.of()));api.answerCallback(id,"🎡",false);return;}',
     'if("a:wheel".equals(d)){api.answerCallback(id,"🎡 برای انتخاب تعداد، /wheel N را بفرستید (۱ تا ۲۰۰).",true);return;}'),
])

edit('games/GameCenter.java', [
    ('        api.sendRichOrText(chat,body,buttons(),true,user,false,"");',
     '        api.sendRichOrText(chat,body,buttons(chat),true,user,false,"");'),
    ('        api.sendRichOrText(chat,"🎮 <b>"+title+" | Simorgh</b>","{\\"inline_keyboard\\":[[{\\"text\\":\\"▶️ اجرا\\",\\"web_app\\":{\\"url\\":"+TelegramClient.q(url)+"}}]]}",true,user,false,"");',
     '        api.sendRichOrText(chat,"🎮 <b>"+title+" | Simorgh</b>",singleButton(chat,url,"▶️ اجرا"),true,user,false,"");'),
    ('    private String buttons(){\n        return "{\\"inline_keyboard\\":[["+',
     '    private String buttons(long chat){\n        if(chat>0) return "{\\"inline_keyboard\\":[["+'),
    ('            "],[{\\"text\\":\\"🎮 Game Center\\",\\"web_app\\":{\\"url\\":"+TelegramClient.q(launcherUrl)+"}}]]}";\n    }',
     '            "],[{\\"text\\":\\"🎮 Game Center\\",\\"web_app\\":{\\"url\\":"+TelegramClient.q(launcherUrl)+"}}]]}";\n        return "{\\"inline_keyboard\\":[["+\n            "{\\"text\\":\\"✈️ Air Raider\\",\\"url\\":"+TelegramClient.q(airUrl)+"},"+\n            "{\\"text\\":\\"🎲 Backgammon\\",\\"url\\":"+TelegramClient.q(backgammonUrl)+"}"+\n            "],[{\\"text\\":\\"🎮 Game Center\\",\\"url\\":"+TelegramClient.q(launcherUrl)+"}]]}";\n    }\n    private static String singleButton(long chat,String url,String text){\n        String kind=chat>0?"\\"web_app\\":{\\"url\\":"+TelegramClient.q(url):"\\"url\\":"+TelegramClient.q(url);\n        return "{\\"inline_keyboard\\":[[{\\"text\\":"+TelegramClient.q(text)+","+kind+"}]]}";\n    }'),
])

# Version markers are deliberately kept compatible with the 4.7.1 source artifact;
# the produced JAR filename/release metadata identifies this as 4.7.3.
print('4.7.3 patch applied')
