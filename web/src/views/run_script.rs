//! The inline client script for the live run page, kept in its own module so `run_page` stays small.
//! Each stage takes minutes, so the page must look alive between events: it subscribes to the SSE
//! stream, marks stages done as they land, and keeps a progress bar, an elapsed-time clock, a spinner
//! on the stage currently crunching, and a phase banner moving. A 4s poll on `/api/runs/:id` is the
//! backstop that surfaces an error (or the final memo) even if the stream drops.

/// Build the page script. `state` is the run's state at render time; `pending_msg` is the banner shown
/// while the run is still `pending` (ingesting / preparing the brief).
pub fn run_js(id: &str, state: &str, pending_msg: &str) -> String {
    format!(
        "const id='{id}',N=10,PEND={pending_msg:?};let t0=Date.now(),clk,pl;\
function qs(s){{return document.querySelector(s);}}\
function stages(){{return[...document.querySelectorAll('ol.stages li')];}}\
function clock(){{const s=Math.floor((Date.now()-t0)/1000);\
qs('#elapsed').textContent=(s/60|0)+':'+('0'+s%60).slice(-2);}}\
function phase(x){{qs('#phase').textContent=x;}}\
function paint(st){{const li=stages(),d=li.filter(x=>x.classList.contains('done')).length;\
qs('#pcount').textContent=d+' / '+N;qs('#pbar>i').style.width=(d/N*100)+'%';\
li.forEach(x=>{{x.classList.remove('active');if(!x.classList.contains('done'))x.querySelector('.v').textContent='';}});\
if(st==='running'){{const nx=li.find(x=>!x.classList.contains('done'));\
if(nx){{nx.classList.add('active');nx.querySelector('.v').innerHTML='<span class=\"spin\"></span>';\
phase('Validating — '+nx.querySelector('.lbl').textContent+'…');}}}}\
else if(st==='pending')phase(PEND);else if(st==='done')phase('Complete ✓');\
else if(st==='cancelled')phase('Cancelled');else if(st==='error')phase('Stopped — see the message above');}}\
function stop(){{clearInterval(clk);clearInterval(pl);}}\
function setState(s){{qs('#state').textContent=s;paint(s);\
if(s==='done'||s==='cancelled'||s==='error')stop();if(s==='done')show();}}\
function show(){{const f=qs('#memo');f.src='/api/runs/'+id+'/report';f.style.display='block';}}\
const es=new EventSource('/api/runs/'+id+'/stream');\
es.addEventListener('stage',e=>{{const d=JSON.parse(e.data),li=document.getElementById('stage-'+d.stage);\
if(li){{li.classList.add('done');li.querySelector('.v').textContent=d.verdict||'done';}}paint('running');}});\
es.addEventListener('done',()=>{{es.close();setState('done');}});\
es.addEventListener('cancelled',()=>{{es.close();setState('cancelled');}});\
async function poll(){{try{{const d=await(await fetch('/api/runs/'+id)).json();\
if(d.state==='error'){{qs('#runerr').textContent=d.error||'failed';setState('error');}}else setState(d.state);}}catch(e){{}}}}\
if('{state}'==='pending'||'{state}'==='running'){{clk=setInterval(clock,1000);clock();}}\
pl=setInterval(poll,4000);setState('{state}');"
    )
}

#[cfg(test)]
mod tests {
    use super::run_js;

    #[test]
    fn wires_the_event_source_and_poll() {
        let js = run_js("r1", "running", "Preparing…");
        assert!(js.contains("EventSource('/api/runs/'+id+'/stream')"));
        assert!(js.contains("'/api/runs/'+id+'/report'"));
        assert!(js.contains("setInterval(poll,4000)"));
    }

    #[test]
    fn drives_the_progress_bar_and_clock() {
        let js = run_js("r1", "pending", "Reading the website…");
        assert!(js.contains("#pbar>i"));
        assert!(js.contains("Reading the website"));
        assert!(js.contains("setInterval(clock,1000)"));
    }
}
