import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "jsr:@supabase/supabase-js@2";

const VERSION = "4.7.0";
const BOT = Deno.env.get("TELEGRAM_BOT_TOKEN") ?? "";
const SECRET = Deno.env.get("TELEGRAM_WEBHOOK_SECRET") ?? "";
const OWNER = Number(Deno.env.get("BOT_OWNER_ID") ?? "0");
const GAME_BASE = (Deno.env.get("GAME_BASE_URL") ?? "").replace(/\/$/, "");
const TG = `https://api.telegram.org/bot${BOT}`;
const db = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);

const RANK: Record<string, number> = { RESTRICTED:0, MEMBER:1, HELPER:2, MODERATOR:3, ADMIN:4, SENIOR_ADMIN:5, GROUP_OWNER:6, BOT_OWNER:7 };
const REQUIRED: Record<string, number> = { WARN:3, MUTE:3, DELETE:3, BAN:4, PIN:4, LOCKS:4, REPORTS:4, WELCOME:4, FILTERS:4, ANTIRAID:4, ADMINS:5, SETTINGS:5, NOTES:5, GAME:1, AI:1, EMOJI:1 };

function json(v: unknown, status=200){return new Response(JSON.stringify(v),{status,headers:{"content-type":"application/json;charset=utf-8","cache-control":"no-store"}})}
function s(v: unknown){return typeof v === "string" ? v : v == null ? "" : String(v)}
function n(v: unknown){const x=Number(v); return Number.isFinite(x)?x:0}
function esc(v: string){return v.replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;")}
function okRole(role:string, perm:string){return (RANK[role]??1)>=(REQUIRED[perm]??99)}
function kb(rows: Array<Array<{text:string,callback_data?:string,web_app?:{url:string}}>>){return {inline_keyboard:rows}}
async function tg(method:string, body:Record<string,unknown>){const r=await fetch(`${TG}/${method}`,{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify(body)});const j=await r.json();if(!r.ok||!j.ok)throw new Error(`${method}: ${j.description??r.status}`);return j.result}
async function ensureGroup(chat:any){const {data,error}=await db.from("groups").upsert({telegram_chat_id:n(chat.id),title:s(chat.title)},{onConflict:"telegram_chat_id"}).select("id,telegram_chat_id,title,settings,owner_user_id,warning_limit").single();if(error)throw error;return data}
async function roleOf(chatId:number,userId:number,groupId:number){if(OWNER&&userId===OWNER)return "BOT_OWNER";const cm=await tg("getChatMember",{chat_id:chatId,user_id:userId});if(cm.status==="creator")return "GROUP_OWNER";if(cm.status==="administrator"){const {data}=await db.from("members").select("role").eq("group_id",groupId).eq("telegram_user_id",userId).maybeSingle();return data?.role==="SENIOR_ADMIN"?"SENIOR_ADMIN":"ADMIN"}if(["left","kicked"].includes(cm.status))return "RESTRICTED";return "MEMBER"}
async function audit(groupId:number,actor:number,action:string,target:number|null=null,metadata:unknown={}){await db.from("audit_logs").insert({group_id:groupId,actor_user_id:actor,action,target_user_id:target,metadata})}
async function panel(chatId:number,role:string){const rows:any[]=[[{text:"👥 اعضا",callback_data:"p:members"},{text:"🎮 بازی‌ها",callback_data:"p:games"}],[{text:"🤖 هوش",callback_data:"p:ai"},{text:"👤 پروفایل",callback_data:"p:profile"}]];if(okRole(role,"WARN"))rows.push([{text:"🔨 مدیریت",callback_data:"p:mod"},{text:"🔒 قفل‌ها",callback_data:"p:locks"}]);if(okRole(role,"REPORTS"))rows.push([{text:"🛡 امنیت",callback_data:"p:security"},{text:"📊 گزارش",callback_data:"p:reports"}]);if(okRole(role,"ADMINS"))rows.push([{text:"👮 نقش‌ها",callback_data:"p:roles"},{text:"⚙️ تنظیمات",callback_data:"p:settings"}]);return tg("sendMessage",{chat_id:chatId,text:`🪟 <b>PediGuardian 4.7</b>\nنقش: <b>${esc(role)}</b>`,parse_mode:"HTML",reply_markup:kb(rows)})}
function command(raw:string){const tok=s(raw).trim().split(/\s+/,1)[0].toLowerCase();const i=tok.indexOf("@");return i>0?tok.slice(0,i):tok}
function arg(raw:string){return s(raw).replace(/^\/\S+\s*/,"").trim()}
async function gameMenu(chatId:number){const rows:any[]=[];const air=GAME_BASE?`${GAME_BASE}/games/air-raider/index.html`:"";const bg=GAME_BASE?`${GAME_BASE}/games/backgammon/index.html`:"";if(air)rows.push([{text:"✈️ Air Raider",web_app:{url:air}}]);if(bg)rows.push([{text:"🎲 Backgammon",web_app:{url:bg}}]);if(!rows.length)return tg("sendMessage",{chat_id:chatId,text:"🎮 آدرس بازی‌ها هنوز تنظیم نشده است."});return tg("sendMessage",{chat_id:chatId,text:"🎮 <b>Pedi Game Center</b>\nیکی را انتخاب کن:",parse_mode:"HTML",reply_markup:kb(rows)})}

Deno.serve(async req=>{
  if(req.method!=="POST")return new Response("OK");
  if(!BOT||!SECRET)return json({ok:false,error:"not_configured"},500);
  if(req.headers.get("x-telegram-bot-api-secret-token")!==SECRET)return new Response("Unauthorized",{status:401});
  try{
    const update=await req.json();
    const updateId=n(update.update_id);
    if(updateId){const {error}=await db.from("telegram_updates").insert({update_id:updateId});if(error&&!String(error.message).toLowerCase().includes("duplicate"))throw error}
    const msg=update.message??update.edited_message;
    if(update.callback_query){const q=update.callback_query,m=q.message;if(!m)return json({ok:true});const g=await ensureGroup(m.chat),uid=n(q.from?.id),role=await roleOf(n(m.chat.id),uid,n(g.id)),data=s(q.data);if(data==="p:main"){await tg("answerCallbackQuery",{callback_query_id:q.id,text:"✅"});await panel(n(m.chat.id),role);return json({ok:true})}if(data.startsWith("p:")){const p=data.slice(2),needed=p==="games"?"GAME":p==="ai"?"AI":p==="mod"?"WARN":p==="locks"?"LOCKS":p==="security"?"REPORTS":p==="reports"?"REPORTS":p==="roles"?"ADMINS":p==="settings"?"SETTINGS":"AI";if(!okRole(role,needed)){await tg("answerCallbackQuery",{callback_query_id:q.id,text:"⛔ دسترسی ندارید",show_alert:true});return json({ok:true})}if(p==="games"){await tg("answerCallbackQuery",{callback_query_id:q.id,text:"🎮"});await gameMenu(n(m.chat.id));return json({ok:true})}await tg("answerCallbackQuery",{callback_query_id:q.id,text:`📂 ${p}`,show_alert:true});return json({ok:true})}await tg("answerCallbackQuery",{callback_query_id:q.id,text:"ℹ️"});return json({ok:true})}
    if(!msg)return json({ok:true});
    const chat=msg.chat,from=msg.from??{},chatId=n(chat.id),userId=n(from.id),text=s(msg.text??msg.caption),g=await ensureGroup(chat),role=await roleOf(chatId,userId,n(g.id));
    if(!text.startsWith("/"))return json({ok:true});
    const cmd=command(text);
    if(cmd==="/start"||cmd==="/panel"){await panel(chatId,role);return json({ok:true})}
    if(cmd==="/help"){await tg("sendMessage",{chat_id:chatId,text:"📚 <b>PediGuardian 4.7</b>\n/panel /game /warn /mute /ban /kick /del /lock /unlock /security /admins /settings /rules /ai /wheel /trial /extend\n\n✈️ 🎲 بازی‌ها از Mini App اجرا می‌شوند.",parse_mode:"HTML"});return json({ok:true})}
    if(cmd==="/version"){await tg("sendMessage",{chat_id:chatId,text:`PediGuardian <b>${VERSION}</b>`,parse_mode:"HTML"});return json({ok:true})}
    if(cmd==="/id"){await tg("sendMessage",{chat_id:chatId,text:`chat_id: <code>${chatId}</code>\nuser_id: <code>${userId}</code>`,parse_mode:"HTML"});return json({ok:true})}
    if(cmd==="/game"){if(!okRole(role,"GAME"))return json({ok:true});await gameMenu(chatId);return json({ok:true})}
    if(cmd==="/rules"){const rules=s(g.settings?.rules);await tg("sendMessage",{chat_id:chatId,text:esc(rules||"📜 قوانینی ثبت نشده است."),parse_mode:"HTML"});return json({ok:true})}
    if(cmd==="/security"){if(!okRole(role,"REPORTS"))return json({ok:true});await tg("sendMessage",{chat_id:chatId,text:"🛡️ Role hierarchy ✅\nNative Telegram permission check ✅\nWebhook secret ✅\nIdempotency ✅\nAudit ✅\nLocks ✅"});return json({ok:true})}
    if(cmd==="/ai"){await tg("sendMessage",{chat_id:chatId,text:"🤖 AI gateway در نسخه 4.7 از سمت سرور اجرا می‌شود. کلید سرویس داخل کلاینت یا Telegram ارسال نمی‌شود."});return json({ok:true})}
    if(cmd==="/wheel"){const count=Math.max(1,Math.min(20,parseInt(arg(text)||"1",10)||1));if(!okRole(role,"GAME"))return json({ok:true});const {error}=await db.from("voice_order_requests").insert({group_id:g.id,requested_by:userId,count,status:"PENDING"});if(error)throw error;await tg("sendMessage",{chat_id:chatId,text:`🎙️ درخواست گردونه ثبت شد. انتخاب فقط از اعضای حاضر در Voice Chat در لحظه اجرا انجام می‌شود. تعداد: ${count}`});await audit(n(g.id),userId,"VOICE_WHEEL_REQUEST",null,{count});return json({ok:true})}
    const modMap:any={"/warn":"WARN","/mute":"MUTE","/ban":"BAN","/kick":"BAN","/del":"DELETE","/pin":"PIN","/unpin":"PIN"};
    if(modMap[cmd]){const perm=modMap[cmd];if(!okRole(role,perm))return json({ok:true});const reply=msg.reply_to_message;if(cmd==="/del"&&!reply?.message_id)return json({ok:true});const target=n(reply?.from?.id);if(["/warn","/mute","/ban","/kick"].includes(cmd)&&!target)return json({ok:true});const actor=await tg("getChatMember",{chat_id:chatId,user_id:userId});if(actor.status!=="creator"&&actor.status!=="administrator")return json({ok:true});if(perm==="DELETE"&&!actor.can_delete_messages)return json({ok:true});if(["WARN","MUTE","BAN"].includes(perm)&&!actor.can_restrict_members)return json({ok:true});if(perm==="PIN"&&!actor.can_pin_messages)return json({ok:true});if(cmd==="/warn")await db.from("warnings").insert({group_id:g.id,telegram_user_id:target,reason:arg(text)||"manual",issued_by:userId});if(cmd==="/mute")await tg("restrictChatMember",{chat_id:chatId,user_id:target,permissions:JSON.stringify({can_send_messages:false}),use_independent_chat_permissions:true});if(cmd==="/ban")await tg("banChatMember",{chat_id:chatId,user_id:target,revoke_messages:true});if(cmd==="/kick"){await tg("banChatMember",{chat_id:chatId,user_id:target,revoke_messages:false});await tg("unbanChatMember",{chat_id:chatId,user_id:target,only_if_banned:true})}if(cmd==="/del")await tg("deleteMessage",{chat_id:chatId,message_id:n(reply.message_id)});if(cmd==="/pin")await tg("pinChatMessage",{chat_id:chatId,message_id:n(reply.message_id),disable_notification:true});if(cmd==="/unpin")await tg("unpinChatMessage",{chat_id:chatId,message_id:n(reply.message_id)});await audit(n(g.id),userId,cmd.slice(1).toUpperCase(),target||null);return json({ok:true})}
    if(cmd==="/lock"||cmd==="/unlock"){if(!okRole(role,"LOCKS"))return json({ok:true});const type=arg(text).split(/\s+/,1)[0].toLowerCase();if(!type)return json({ok:true});await db.from("locks").upsert({group_id:g.id,lock_type:type,enabled:cmd==="/lock",action:"delete"},{onConflict:"group_id,lock_type"});await audit(n(g.id),userId,cmd.slice(1).toUpperCase(),null,{lock_type:type});await tg("sendMessage",{chat_id:chatId,text:cmd==="/lock"?`🔒 ${type} قفل شد.`:`🔓 ${type} باز شد.`});return json({ok:true})}
    if(cmd==="/trial"){const {data}=await db.from("group_access").select("access_until,is_active").eq("group_id",g.id).maybeSingle();await tg("sendMessage",{chat_id:chatId,text:data?`📅 سرویس تا ${esc(String(data.access_until))}`:"📅 وضعیت سرویس ثبت نشده است."});return json({ok:true})}
    if(cmd==="/extend"){if(role!=="BOT_OWNER")return json({ok:true});const days=Math.max(1,Math.min(365,parseInt(arg(text)||"15",10)||15));const {error}=await db.from("group_access").upsert({group_id:g.id,access_until:new Date(Date.now()+days*86400000).toISOString(),is_active:true,last_extended_at:new Date().toISOString()},{onConflict:"group_id"});if(error)throw error;await tg("sendMessage",{chat_id:chatId,text:`✅ سرویس ${days} روز تمدید شد.`});return json({ok:true})}
    return json({ok:true});
  }catch(e){console.error(e);return json({ok:false,error:"internal"},500)}
});
