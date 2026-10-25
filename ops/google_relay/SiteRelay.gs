/** Site-approved messages -> existing Telegram bot; private outbound polling. */
function kxSiteRelayConfig_() {
  var props = kxProps_();
  var url = kxString_(props.getProperty('KX_SITE_RELAY_URL')).replace(/\/+$/, '');
  var key = kxString_(props.getProperty('KX_SITE_RELAY_KEY'));
  var chat = kxString_(props.getProperty('KX_SITE_RELAY_CHAT_ID'));
  kxAssert_(/^https:\/\/[A-Za-z0-9.-]+(?::443)?$/.test(url), 'آدرس اصلی HTTPS سایت را بدون مسیر یا پارامتر وارد کنید.');
  kxAssert_(/^[a-f0-9]{64}$/.test(key), 'کلید اتصال سایت باید ۶۴ نویسه هگز باشد.');
  kxAssert_(/^@[A-Za-z0-9_]{4,}$/.test(chat) || /^-100\d+$/.test(chat), 'شناسه کانال معتبر نیست.');
  return { url: url, key: key, chat: chat };
}

function kxSiteRelayRequest_(action, payload) {
  var cfg = kxSiteRelayConfig_();
  var response;
  try {
    response = UrlFetchApp.fetch(cfg.url + '/api/messaging/market-relay/' + action + '/', {
      method: 'post', contentType: 'application/json',
      headers: { Authorization: 'Bearer ' + cfg.key },
      payload: JSON.stringify(payload || {}), muteHttpExceptions: true,
      followRedirects: false, validateHttpsCertificates: true, timeoutSeconds: 15
    });
  } catch (error) {
    // Never expose request exceptions; they may contain a credential or URL.
    throw new Error('ارتباط واسط با سایت برقرار نشد.');
  }
  var code = response.getResponseCode();
  var parsed = kxParseJson_(response.getContentText(), null);
  if (code !== 200 || !parsed || typeof parsed !== 'object') {
    var failure = new Error('پاسخ سایت معتبر نیست (HTTP ' + code + ').');
    failure.relayHttpCode = code;
    throw failure;
  }
  return parsed;
}

function kxSiteRelayAck_(pending) {
  var result;
  try {
    result = kxSiteRelayRequest_('ack', { id: pending.id, receipt: pending.receipt,
      status: pending.status, message_id: pending.message_id || '' });
  } catch (error) {
    if (error.relayHttpCode === 409) {
      // The operator may have resolved this attempt. Do not block later jobs
      // and never resend this one. The site keeps the uncertain state.
      kxProps_().deleteProperty('KX_SITE_RELAY_PENDING');
    }
    throw error;
  }
  kxAssert_(result.ok === true, 'ثبت رسید در سایت تأیید نشد.');
  kxProps_().deleteProperty('KX_SITE_RELAY_PENDING');
}

function runKavexSiteRelay() {
  try {
    return kxWithLock_(function () {
      var cfg = kxSiteRelayConfig_();
      kxBotToken_();
      var saved = kxProps_().getProperty('KX_SITE_RELAY_PENDING');
      if (saved) {
        var pending = kxParseJson_(saved, null);
        kxAssert_(pending && pending.id && pending.receipt, 'رسید محلی معتبر نیست؛ وضعیت کانال را بررسی کنید.');
        // A previous execution stopped at an unknown point in sendMessage.
        if (pending.status === 'sending') pending.status = 'unknown';
        kxSiteRelayAck_(pending);
      }
      var started = Date.now();
      var processed = 0;
      while (processed < 3 && Date.now() - started < 45000) {
        var claimed = kxSiteRelayRequest_('claim', {});
        if (claimed.job === null) break;
        var job = claimed.job;
        kxAssert_(job && job.id && job.receipt, 'پاسخ صف سایت معتبر نیست.');
        var checkpoint = { id: job.id, receipt: job.receipt, status: 'sending', message_id: '' };
        // Persist BEFORE a send, and retain it until the site acknowledges.
        kxProps_().setProperty('KX_SITE_RELAY_PENDING', JSON.stringify(checkpoint));
        if (kxString_(job.chat_id) !== cfg.chat || !job.text ||
            typeof job.text !== 'string' || job.text.length > 4000 ||
            !isFinite(Date.parse(job.expires_at)) || Date.parse(job.expires_at) <= Date.now() + 15000) {
          checkpoint.status = 'failed';
        } else {
          try {
            var message = kxTelegramRequest_('sendMessage', {
              chat_id: cfg.chat, text: job.text, disable_web_page_preview: true
            });
            kxAssert_(message && /^[1-9]\d*$/.test(kxString_(message.message_id)), 'شناسه ارسال معتبر نیست.');
            checkpoint.message_id = kxString_(message.message_id);
            checkpoint.status = 'sent';
          } catch (sendError) {
            checkpoint.status = /\(HTTP (?:400|401|403|404|429)\)/.test(kxString_(sendError.message)) ? 'failed' : 'unknown';
          }
        }
        kxProps_().setProperty('KX_SITE_RELAY_PENDING', JSON.stringify(checkpoint));
        kxSiteRelayAck_(checkpoint);
        processed++;
        if (processed < 3) Utilities.sleep(1100);
      }
      kxProps_().setProperty('KX_SITE_RELAY_LAST_POLL', kxNowIso_());
      kxProps_().deleteProperty('KX_SITE_RELAY_ERROR');
      return { processed: processed };
    });
  } catch (error) {
    kxProps_().setProperty('KX_SITE_RELAY_ERROR', 'دریافت یا ثبت نتیجه ناموفق بود؛ اتصال سایت و وضعیت صف را بررسی کنید.');
    throw new Error('واسط سایت کامل اجرا نشد؛ وضعیت اتصال سایت و صف پیام‌ها را بررسی کنید.');
  }
}

function configureKavexSiteRelay() {
  var ui = SpreadsheetApp.getUi();
  var inputs = [
    ['KX_SITE_RELAY_URL', 'آدرس اصلی سایت', 'مثال: https://kavehmetal.com — بدون /api یا مسیر دیگر'],
    ['KX_SITE_RELAY_KEY', 'کلید اتصال سایت', 'همان کلید ۶۴ نویسه‌ای ساخته‌شده در پنل کانال سایت را وارد کنید.'],
    ['KX_SITE_RELAY_CHAT_ID', 'شناسه کانال سایت', 'دقیقاً همان مقصد تنظیم‌شده در سایت؛ مثلاً @kavehmetal. ربات باید مدیر همین کانال باشد.']
  ];
  var values = {};
  for (var i = 0; i < inputs.length; i++) {
    var answer = ui.prompt(inputs[i][1], inputs[i][2], ui.ButtonSet.OK_CANCEL);
    if (answer.getSelectedButton() !== ui.Button.OK) return;
    values[inputs[i][0]] = kxString_(answer.getResponseText()).trim();
  }
  kxAssert_(/^https:\/\/[A-Za-z0-9.-]+(?::443)?\/?$/.test(values.KX_SITE_RELAY_URL), 'فقط آدرس اصلی HTTPS سایت مجاز است.');
  kxAssert_(/^[a-f0-9]{64}$/.test(values.KX_SITE_RELAY_KEY), 'کلید اتصال معتبر نیست.');
  kxAssert_(/^@[A-Za-z0-9_]{4,}$|^-100\d+$/.test(values.KX_SITE_RELAY_CHAT_ID), 'شناسه کانال معتبر نیست.');
  kxWithLock_(function () {
    if (kxProps_().getProperty('KX_SITE_RELAY_PENDING')) {
      kxAssert_(values.KX_SITE_RELAY_URL.replace(/\/+$/, '') === kxString_(kxProps_().getProperty('KX_SITE_RELAY_URL')).replace(/\/+$/, '') &&
        values.KX_SITE_RELAY_CHAT_ID === kxProps_().getProperty('KX_SITE_RELAY_CHAT_ID'),
        'رسید منتظر ثبت وجود دارد؛ تا ثبت رسید، سایت و مقصد را تغییر ندهید. تغییر کلید همان اتصال مجاز است.');
    }
    Object.keys(values).forEach(function (key) { kxProps_().setProperty(key, values[key]); });
  });
  ui.alert('تنظیمات سایت ذخیره شد. اکنون «فعال‌سازی دریافت پیام‌های سایت» را اجرا کنید.');
}

function activateKavexSiteRelay() {
  kxSiteRelayConfig_();
  kxBotToken_();
  kxWithLock_(function () { kxEnsureClockTrigger_('runKavexSiteRelay', 1); });
  SpreadsheetApp.getUi().alert('دریافت صف سایت تقریباً هر دقیقه فعال شد. در هر اجرا حداکثر ۳ پیام تأییدشده ارسال می‌شود. Web App یا تغییر Webhook لازم نیست.');
}

function stopKavexSiteRelay() {
  kxWithLock_(function () { kxRemoveTriggers_('runKavexSiteRelay'); });
  SpreadsheetApp.getUi().alert('دریافت پیام‌های سایت متوقف شد.');
}

function showKavexSiteRelayInfo() {
  var props = kxProps_();
  SpreadsheetApp.getUi().alert('آخرین دریافت موفق: ' + (props.getProperty('KX_SITE_RELAY_LAST_POLL') || 'هنوز اجرا نشده') +
    '\nرسید منتظر ثبت: ' + (props.getProperty('KX_SITE_RELAY_PENDING') ? 'بله؛ دریافت سایت را اجرا کنید' : 'خیر') +
    '\nوضعیت: ' + (props.getProperty('KX_SITE_RELAY_ERROR') || 'خطایی ثبت نشده'));
}
