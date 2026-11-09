import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import vm from 'node:vm'

function worker(fetcher = async () => { throw new Error('offline') }) {
  const handlers = {}, cached = [], matched = []
  const context = vm.createContext({ URL, console, self: {location: {origin:'https://app.example.test'}, addEventListener: (event, fn) => {handlers[event]=fn}, clients: {claim:async()=>{}} }, fetch: fetcher, caches: {open: async()=>({addAll: async urls=>cached.push(...urls)}), keys:async()=>[], match: async path=>{matched.push(path);return {offline:true}}} })
  vm.runInContext(fs.readFileSync('public/sw.js','utf8'),context)
  return {handlers,cached,matched}
}

test('manifest has installable icons at correct dimensions', () => {
  const m=JSON.parse(fs.readFileSync('public/manifest.webmanifest','utf8'))
  assert.equal(m.display,'standalone'); assert.equal(m.scope,'/'); assert(m.icons.some(i=>i.purpose==='maskable'))
  for(const icon of m.icons){const bytes=fs.readFileSync('public'+icon.src); const size=Number(icon.sizes.split('x')[0]); assert.equal(bytes.readUInt32BE(16),size);assert.equal(bytes.readUInt32BE(20),size)}
})
test('service worker does not intercept protected API or document requests', () => {
  const {handlers}=worker()
  for(const path of ['/api/dependents','/api/documents/123/file','/api/v1/me','/api/v1/family/schedule']){
    let intercepted=false
    handlers.fetch({request:{url:'https://app.example.test'+path,method:'GET',mode:'cors'},respondWith:()=>{intercepted=true}})
    assert.equal(intercepted,false,path)
  }
})
test('offline navigation renders a public fallback rather than cached health records', async () => {
  const {handlers,matched}=worker(); let response
  handlers.fetch({request:{url:'https://app.example.test/',method:'GET',mode:'navigate'},respondWith:r=>{response=r}})
  assert.deepEqual(await response,{offline:true});assert.deepEqual(matched,['/offline.html'])
})
test('install precaches only public assets', async () => {
  const {handlers,cached}=worker();let done
  handlers.install({waitUntil:p=>{done=p}});await done
  assert(cached.includes('/offline.html'));assert(cached.every(p=>!p.startsWith('/api/')))
})
