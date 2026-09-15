from pathlib import Path
import runpy

# Reapply the reviewed 4.7.3 safety fixes first.
runpy.run_path('patches/build-4.7.3.py')

ROOT = Path('source/src/main/java/ir/pedirany/guardian')

def edit(rel, replacements):
    path = ROOT / rel
    text = path.read_text(encoding='utf-8')
    for old, new in replacements:
        if old not in text:
            raise SystemExit(f'4.7.4 patch anchor not found in {path}: {old[:120]!r}')
        text = text.replace(old, new, 1)
    path.write_text(text, encoding='utf-8')

edit('ai/AiService.java', [
    ('private final List<Provider> providers=new ArrayList<>(); private final Map<String,Integer> failures=new HashMap<>(); private final Map<String,Long> openUntil=new HashMap<>();',
     'private final List<Provider> providers=new ArrayList<>(); private final Map<String,Integer> failures=new HashMap<>(); private final Map<String,Long> openUntil=new HashMap<>();\n'
     '    private final Map<String,Deque<String>> memory=new LinkedHashMap<>();\n'
     '    private static final int MAX_TURNS=parseIntEnv("AI_MEMORY_TURNS",6,1,12);\n'
     '    private static final int MAX_CONTEXT_CHARS=parseIntEnv("AI_MEMORY_CHARS",8000,1000,24000);'),
    ('public synchronized String ask(String prompt)throws Exception{',
     'public synchronized String ask(String prompt)throws Exception{return ask(0L,0L,prompt);}\n'
     '    public synchronized String ask(long chatId,long userId,String prompt)throws Exception{'),
    ('if(prompt==null||prompt.isBlank())throw new IllegalArgumentException("empty prompt");\n        providers.sort(Comparator.comparingInt(Provider::priority)); Exception last=null;',
     'if(prompt==null||prompt.isBlank())throw new IllegalArgumentException("empty prompt");\n'
     '        String key=chatId+":"+userId;\n'
     '        String effectivePrompt=withMemory(key,prompt);\n'
     '        providers.sort(Comparator.comparingInt(Provider::priority)); Exception last=null;'),
    ('case "groq"->groq(p,prompt);case "gemini"->gemini(p,prompt);case "openai"->openai(p,prompt);case "xai"->openaiCompat("https://api.x.ai/v1/chat/completions",p,prompt);case "openrouter"->openaiCompat("https://openrouter.ai/api/v1/chat/completions",p,prompt);',
     'case "groq"->groq(p,effectivePrompt);case "gemini"->gemini(p,effectivePrompt);case "openai"->openai(p,effectivePrompt);case "xai"->openaiCompat("https://api.x.ai/v1/chat/completions",p,effectivePrompt);case "openrouter"->openaiCompat("https://openrouter.ai/api/v1/chat/completions",p,effectivePrompt);'),
    ('failures.put(p.name,0); return out+"\\n\\n🤖 AI: "+p.name+"/"+p.model;',
     'failures.put(p.name,0); remember(key,prompt,out); return out+"\\n\\n🤖 AI: "+p.name+"/"+p.model;'),
    ('private static String q(String s){',
     'private synchronized String withMemory(String key,String prompt){\n'
     '        Deque<String> turns=memory.get(key);\n'
     '        if(turns==null||turns.isEmpty())return prompt;\n'
     '        StringBuilder b=new StringBuilder("Conversation context (use only as context; answer the latest user request):\\n");\n'
     '        for(String turn:turns){ if(b.length()+turn.length()+2>MAX_CONTEXT_CHARS)break; b.append(turn).append(\'\\n\'); }\n'
     '        b.append("User: ").append(prompt);\n'
     '        return b.toString();\n'
     '    }\n'
     '    private synchronized void remember(String key,String prompt,String answer){\n'
     '        Deque<String> turns=memory.computeIfAbsent(key,k->new ArrayDeque<>());\n'
     '        turns.addLast("User: "+trim(prompt));\n'
     '        turns.addLast("Assistant: "+trim(answer));\n'
     '        while(turns.size()>MAX_TURNS*2)turns.removeFirst();\n'
     '        while(memory.size()>500)memory.remove(memory.keySet().iterator().next());\n'
     '    }\n'
     '    private static String trim(String s){ if(s==null)return ""; String v=s.replace(\'\\n\',\' \').replace(\'\\r\',\' \').trim(); return v.length()>2000?v.substring(0,2000):v; }\n'
     '    private static String q(String s){'),
    ('private static String env(String k,String d){String v=System.getenv(k);return v==null||v.isBlank()?d:v;}\n}',
     'private static String env(String k,String d){String v=System.getenv(k);return v==null||v.isBlank()?d:v;}\n'
     '    private static int parseIntEnv(String key,int def,int min,int max){try{return Math.max(min,Math.min(max,Integer.parseInt(env(key,String.valueOf(def)))));}catch(Exception e){return def;}}\n}'),
])

# Scope AI memory to chat + user; never share group conversation context across users.
edit('commands/handlers/FeatureHandler.java', [
    ('String answer=ai.ask(p);', 'String answer=ai.ask(c.chatId(),c.userId(),p);'),
])

# Current Bot API update names. This only changes the client's allow-list; no webhook is changed or registered.
edit('telegram/TelegramClient.java', [
    ('private volatile Long botIdCache;',
     'private volatile Long botIdCache;\n'
     '    private static final String MODERN_ALLOWED_UPDATES = "[\\"message\\",\\"edited_message\\",\\"channel_post\\",\\"edited_channel_post\\",\\"business_connection\\",\\"business_message\\",\\"edited_business_message\\",\\"deleted_business_messages\\",\\"guest_message\\",\\"inline_query\\",\\"chosen_inline_result\\",\\"callback_query\\",\\"chat_member\\",\\"my_chat_member\\",\\"chat_join_request\\",\\"message_reaction\\",\\"message_reaction_count\\",\\"chat_boost\\",\\"removed_chat_boost\\",\\"managed_bot\\",\\"subscription\\",\\"stopped_message_generation\\"]";'),
    ('"allowed_updates", "[\\"message\\",\\"edited_message\\",\\"callback_query\\",\\"my_chat_member\\",\\"chat_member\\",\\"chat_join_request\\"]"));',
     '"allowed_updates", MODERN_ALLOWED_UPDATES));'),
])

for rel in ['commands/handlers/GeneralHandler.java','games/GameCenter.java']:
    path=ROOT/rel
    path.write_text(path.read_text(encoding='utf-8').replace('4.7.3','4.7.4'),encoding='utf-8')

pom=Path('source/pom.xml')
pom.write_text(pom.read_text(encoding='utf-8').replace('<version>4.7.3</version>','<version>4.7.4</version>',1),encoding='utf-8')
print('4.7.4 patch applied')
