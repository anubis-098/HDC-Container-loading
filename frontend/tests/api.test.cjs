const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const ts=require('typescript');
const source=ts.transpileModule(fs.readFileSync(path.join(__dirname,'../src/lib/api.ts'),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
function harness(fetch){
 const timers=[],cleared=[];
 const sandbox={exports:{},Headers,Response,FormData,AbortController,fetch,setTimeout(callback,delay){timers.push({callback,delay});return timers.length;},clearTimeout(id){cleared.push(id);}};
 vm.runInNewContext(source,sandbox);
 return {...sandbox.exports,timers,cleared};
}
const stalled=(_path,{signal})=>new Promise((resolve,reject)=>{
 if(signal.aborted)reject(new Error('aborted'));
 else signal.addEventListener('abort',()=>reject(new Error('aborted')),{once:true});
});
test('JSON requests keep credentials, encode headers and clear their timer',async()=>{
 let request;
 const h=harness(async(path,options)=>{request={path,options};return new Response('{"ok":true}');});
 assert.equal((await h.api('/test',{method:'POST',body:'{}'})).ok,true);
 assert.equal(request.path,'/api/test');assert.equal(request.options.credentials,'same-origin');
 assert.equal(request.options.headers.get('Content-Type'),'application/json');
 assert.equal(h.timers[0].delay,30000);assert.deepEqual(h.cleared,[1]);
});
test('Stalled requests time out and photo uploads receive a longer deadline',async()=>{
 for(const [body,delay] of [[undefined,30000],[new FormData(),90000]]){
  const h=harness(stalled),pending=h.api('/test',{body});
  assert.equal(h.timers[0].delay,delay);h.timers[0].callback();
  await assert.rejects(pending,error=>error.status===0);
  assert.deepEqual(h.cleared,[1]);
 }
});
test('Caller cancellation is forwarded without waiting for the deadline',async()=>{
 const controller=new AbortController(),h=harness(stalled);
 const pending=h.api('/test',{signal:controller.signal});controller.abort();
 await assert.rejects(pending,error=>error.status===0);assert.deepEqual(h.cleared,[1]);
});
test('HTTP authorization errors retain their status and message',async()=>{
 const h=harness(async()=>new Response('{"detail":"Login required"}',{status:401}));
 await assert.rejects(h.api('/test'),error=>error.status===401&&error.message==='Login required');
 assert.deepEqual(h.cleared,[1]);
});
test('The deadline also covers a stalled JSON response body',async()=>{
 const h=harness(async(path,options)=>({ok:true,json:()=>stalled(path,options)}));
 const pending=h.api('/test');await Promise.resolve();
 h.timers[0].callback();await assert.rejects(pending,error=>error.status===0);
 assert.deepEqual(h.cleared,[1]);
});
