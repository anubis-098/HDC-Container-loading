const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
const ts=require('typescript'),React=require('react'),{renderToStaticMarkup}=require('react-dom/server');
const source=ts.transpileModule(fs.readFileSync(path.join(__dirname,'../src/components/TripPallets.tsx'),'utf8'),{
  compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX},
}).outputText;
function render(status='OPEN',online=true){
 const exported={};
 new Function('require','exports',source)(name=>{
  if(name==='./StorePicker')return {StorePicker:()=>null};
  if(name==='../lib/api')return {uid:()=> 'request-id'};
  if(name==='./PhotoTile')return {PhotoTile:props=>React.createElement('div',null,props.label)};
  if(name==='./ui/button')return {Button:({variant,...props})=>React.createElement('button',props)};
  return require(name);
 },exported);
 return renderToStaticMarkup(React.createElement(exported.TripPallets,{
  trip:{id:'trip',status,pallets:[{id:'p1',number:1,store_code:'001',store_name:'Store',orders:['ORDER-1'],photos:[{id:'photo-1'}]}]},
  stores:[],pending:[],disabled:false,canCapture:true,canDelete:online,
  onUpdated(){},onCapture(){},onDiscard(){},onDelete(){},onEditingChange(){},
 }));
}
test('Uploaded photos can be deleted only while the Trip is open',()=>{
 const html=render();
 assert.ok(html.includes('pallet-photo-delete'));
 assert.match(html,/class="[^"]*lucide[^"]*trash[^"]*"/);
 for(const status of ['DONE','CANCELLED'])assert.ok(!render(status).includes('pallet-photo-delete'));
});
test('Offline mode disables deletion while keeping photo capture available',()=>{
 const html=render('OPEN',false);
 const button=html.match(/<button[^>]*class="pallet-photo-delete"[^>]*>/)[0];
 assert.ok(button.includes('disabled'));
 const inputs=html.match(/<input[^>]*type="file"[^>]*>/g);
 assert.equal(inputs.length,2);
 assert.ok(inputs.every(input=>!input.includes('disabled')));
});
