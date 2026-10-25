const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.existsSync(__dirname + '/SiteRelay.gs') ? fs.readFileSync(__dirname + '/SiteRelay.gs', 'utf8') : '';

function harness() {
  const props = new Map([['KX_SITE_RELAY_URL', 'https://example.test'], ['KX_SITE_RELAY_KEY', 'a1'.repeat(32)], ['KX_SITE_RELAY_CHAT_ID', '@approved']]);
  const calls = [], sent = [];
  const state = { jobs: [{ id: 'aaa', receipt: 'receipt', chat_id: '@approved', text: 'Exact approved text', expires_at: new Date(Date.now()+300000).toISOString() }], failAck: false, failSend: false };
  const ctx = vm.createContext({
    kxProps_: () => ({ getProperty: k => props.get(k) ?? null, setProperty: (k,v) => props.set(k,String(v)), deleteProperty: k=>props.delete(k) }),
    kxString_: v => v == null ? '' : String(v),
    kxAssert_: (value, message) => { if (!value) throw new Error(message); },
    kxParseJson_: (v,fallback) => { try{return JSON.parse(v);}catch{return fallback;} },
    kxWithLock_: fn=>fn(), kxNowIso_: ()=>new Date().toISOString(),
    kxBotToken_: ()=>'bot-secret',
    kxTelegramRequest_: (method, payload) => { if(state.failSend) throw new Error('network'); sent.push({method,payload}); return {message_id:42}; },
    UrlFetchApp: { fetch(url, opts) {
      calls.push({url,opts});
      if (url.endsWith('/ack/') && state.failAck) throw new Error('sensitive request: '+opts.headers.Authorization);
      const data=url.endsWith('/claim/')?{job:state.jobs.shift() || null}:{ok:true};
      return {getResponseCode:()=>200,getContentText:()=>JSON.stringify(data)};
    } },
  });
  vm.runInContext(source,ctx);
  return {ctx,props,calls,sent,state};
}

test('relay sends the exact approved text to the pinned channel once',()=>{
  const h=harness(); h.ctx.runKavexSiteRelay(); h.ctx.runKavexSiteRelay();
  assert.equal(h.sent.length,1); assert.equal(h.sent[0].payload.text,'Exact approved text');
  assert.equal(h.sent[0].payload.chat_id,'@approved');
  assert.ok(h.calls.every(c=>c.opts.followRedirects===false));
});
test('ack timeout retries only acknowledgement, never Telegram delivery',()=>{
  const h=harness(); h.state.failAck=true;
  assert.throws(()=>h.ctx.runKavexSiteRelay()); assert.equal(h.sent.length,1);
  h.state.failAck=false; h.ctx.runKavexSiteRelay(); assert.equal(h.sent.length,1);
  assert.ok(![...h.props.values()].some(v=>v.includes('sensitive request')));
});
test('recovered sending checkpoint is reported as unknown without sending again',()=>{
  const h=harness();h.state.jobs=[];
  h.props.set('KX_SITE_RELAY_PENDING',JSON.stringify({id:'aaa',receipt:'receipt',status:'sending'}));
  h.ctx.runKavexSiteRelay(); assert.equal(h.sent.length,0);
  assert.equal(JSON.parse(h.calls[0].opts.payload).status,'unknown');
});
test('destination mismatch is rejected before any Telegram call',()=>{
  const h=harness();h.state.jobs[0].chat_id='@outsider';h.ctx.runKavexSiteRelay();
  assert.equal(h.sent.length,0);assert.equal(JSON.parse(h.calls.find(c=>c.url.endsWith('/ack/')).opts.payload).status,'failed');
});
