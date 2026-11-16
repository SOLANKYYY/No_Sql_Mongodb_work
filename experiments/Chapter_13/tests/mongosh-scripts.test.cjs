// Simulated command behavior only: this is not a live MongoDB deployment test.
// Deliberately do NOT inject an assert global into either script's environment.
const fs=require('fs'), vm=require('vm'), assert=require('node:assert/strict'), path=require('path');
const root=path.join(__dirname,'..');
const bootstrap=fs.readFileSync(path.join(root,'scripts/bootstrap.js'),'utf8');
const recovery=fs.readFileSync(path.join(root,'scripts/k8s-check.js'),'utf8');
const env={RS_HOSTS:'mongo1:27017,mongo2:27017,mongo3:27017',MONGO_ADMIN_USER:'test',MONGO_ADMIN_PASSWORD:'test',MONGO_APP_PASSWORD:'test',MONGO_MONITOR_PASSWORD:'test'};
const members=[0,1,2].map(i=>({name:'mongo'+(i+1),stateStr:i===0?'PRIMARY':'SECONDARY',health:1}));
let count=0;
function test(name,fn){fn();count++;console.log('PASS '+name);}
function bootstrapCase(mode){
 let created=0, initiated=0, added=0, printed=0;
 const local={auth(){if(mode==='existing')return {ok:1};return created?{ok:1}:{ok:0};},
  runCommand(c){
   if(c.replSetGetStatus){
    if(mode==='partial')return {ok:1};
    if(mode==='denied')throw Object.assign(new Error('Unauthorized'),{code:13});
    throw Object.assign(new Error('NotYetInitialized'),mode==='name'?{codeName:'NotYetInitialized'}:{code:94});
   }
   if(c.replSetInitiate){initiated++;return mode==='failed-init'?{ok:0}:{ok:1};}
   if(c.hello)return {ok:1,isWritablePrimary:true};
  },createUser(){created++;}};
 const admin={getUser(){return null;},createUser(){added++;},runCommand(){return {ok:1,members};}};
 const ctx={process:{env},db:{getSiblingDB(){return local;}},sleep(){},print(){printed++;},Mongo:function(){this.getDB=()=>admin;}};
 if(mode==='denied'||mode==='failed-init'){
  assert.throws(()=>vm.runInNewContext(bootstrap,ctx));assert.equal(created,0);assert.equal(printed,0);
 }else{
  vm.runInNewContext(bootstrap,ctx);assert.equal(created,mode==='existing'?0:1);
  assert.equal(initiated,['partial','existing'].includes(mode)?0:1);assert.equal(added,2);assert.equal(printed,1);
 }
}
for(const mode of ['first-run','name','partial','existing','denied','failed-init'])test('bootstrap '+mode,()=>bootstrapCase(mode));
function recoveryCase(mode){
 let printed=0,writes=0;
 const db={sentinel:{findOne(){return mode==='missing'?null:{value:'survives-pod-recreation'};}},runCommand(c){
  if(c.update){writes++; if(mode==='write-concern')return {ok:1,writeConcernError:{code:64}}; if(mode==='write-error')return {ok:1,writeErrors:[{code:121}]};return {ok:1};}
  return {ok:1,members:mode==='unhealthy'?members.slice(0,2):members};
 }};
 const ctx={process:{env:{...env,CHECK_ACTION:mode==='status'?'status':'seed'}},print(){printed++;},Mongo:function(){this.getDB=()=>db;this.setReadPref=()=>{};}};
 if(['missing','unhealthy','write-concern','write-error'].includes(mode)){assert.throws(()=>vm.runInNewContext(recovery,ctx));assert.equal(printed,0);}
 else {vm.runInNewContext(recovery,ctx);assert.equal(printed,1);assert.equal(writes,mode==='status'?0:1);}
}
for(const mode of ['seed','status','missing','unhealthy','write-concern','write-error'])test('recovery '+mode,()=>recoveryCase(mode));
assert(!/\bassert\s*[.(]/.test(bootstrap+recovery));
console.log(count+' simulated cases passed without a shell assert global. Live execution remains required.');
