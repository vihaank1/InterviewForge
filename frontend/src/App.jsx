import {useState} from 'react';
import {api, post} from './api.js';
import Diagram from './Diagram.jsx';

const TRACKS=['backend','frontend','systems','ml','general'];
function Details({title,items}) {
  return Array.isArray(items)&&items.length ? <section><h3>{title}</h3><ul>{items.map((item,i)=><li key={i}>{item}</li>)}</ul></section> : null;
}
export default function App() {
  const [tab,setTab]=useState('interview');
  const [role,setRole]=useState('Backend Engineer');
  const [track,setTrack]=useState('backend');
  const [difficulty,setDifficulty]=useState('Medium');
  const [session,setSession]=useState(null);
  const [answer,setAnswer]=useState('');
  const [prompt,setPrompt]=useState('Design a scalable photo-sharing feed for one million users');
  const [candidate,setCandidate]=useState('');
  const [design,setDesign]=useState(null);
  const [loading,setLoading]=useState(false);
  const [error,setError]=useState('');
  async function perform(action) {
    setLoading(true);setError('');
    try { await action(); } catch(e) {setError(e.message||'Request failed');}
    finally {setLoading(false);}
  }
  async function start() {
    await perform(async()=>{
      const s=await post('/sessions',{role,track,difficulty});
      setSession(s);setAnswer('');localStorage.setItem('interviewforge-last-session',s.id);
    });
  }
  async function resume() {
    const id=localStorage.getItem('interviewforge-last-session');
    if(!id){setError('No locally saved session ID found.');return;}
    await perform(async()=>setSession(await api('/sessions/'+encodeURIComponent(id))));
  }
  async function submit() {
    if (!session || answer.trim().length<3) return;
    await perform(async()=>{
      setSession(await post('/sessions/'+session.id+'/answers',{answer}));
      setAnswer('');
    });
  }
  async function complete() {
    if(!session) return;
    await perform(async()=>setSession(await post('/sessions/'+session.id+'/complete')));
  }
  async function generate() {
    await perform(async()=>setDesign(await post('/designs',{prompt,candidate_design:candidate.trim()||null})));
  }
  async function review() {
    if(!design)return;
    await perform(async()=>setDesign(await post('/designs/'+design.id+'/review')));
  }
  const last=session?.history?.at(-1);
  return <main className="shell">
    <header><p className="eyebrow">AI INTERVIEW PRACTICE · ENGINEERING WORKFLOWS</p><h1>InterviewForge</h1><p className="intro">Practice technical interviews that build on your answers—and stress-test architecture decisions with structured review.</p></header>
    <nav><button className={tab==='interview'?'active':''} onClick={()=>setTab('interview')}>Interview room</button><button className={tab==='design'?'active':''} onClick={()=>setTab('design')}>System design lab</button></nav>
    {error&&<p role="alert" className="error">{error}</p>}
    {tab==='interview'?<>
      <div className="panel"><h2>Configure your interview</h2><div className="fields"><label>Role<input value={role} onChange={e=>setRole(e.target.value)}/></label><label>Track<select value={track} onChange={e=>setTrack(e.target.value)}>{TRACKS.map(t=><option key={t} value={t}>{t}</option>)}</select></label><label>Difficulty<select value={difficulty} onChange={e=>setDifficulty(e.target.value)}>{['Easy','Medium','Hard'].map(x=><option key={x}>{x}</option>)}</select></label></div><div className="actions"><button disabled={loading||role.trim().length<2} onClick={start}>Start new interview</button><button className="muted-btn" disabled={loading} onClick={resume}>Resume last session</button></div></div>
      {session&&<><div className="panel"><div className="between"><h2>Round {session.round}</h2><span className="tag">{session.status}</span></div><p className="question">{session.question}</p><p className="muted">Focus: {session.focus}</p>{session.status==='active'&&<><label>Your answer<textarea rows="7" value={answer} onChange={e=>setAnswer(e.target.value)} placeholder="Explain your approach, trade-offs, and reasoning…"/></label><div className="actions"><button disabled={loading||answer.trim().length<3} onClick={submit}>{loading?'Working…':'Submit answer & continue'}</button><button className="muted-btn" disabled={loading} onClick={complete}>Finish session</button></div></>}</div>
      <div className="panel"><h2>Progress</h2><div className="stats"><div><b>{session.progress?.completed_rounds??0}</b><span>Completed rounds</span></div><div><b>{session.progress?.average_score??'—'}</b><span>Average / 10</span></div></div><Details title="Recent weak spots" items={session.progress?.weak_spots}/></div>
      {last&&<div className="panel"><h2>Previous answer feedback</h2><p className="score">Score: {last.score}/10</p><p>{last.evaluation.feedback}</p><Details title="Strengths" items={last.evaluation.strengths}/><Details title="Improve next" items={last.evaluation.improvements}/><Details title="Weak spots" items={last.evaluation.weak_spots}/></div>}</>}
    </>:<>
      <div className="panel"><h2>Architecture challenge</h2><label>System to design<textarea rows="3" value={prompt} onChange={e=>setPrompt(e.target.value)}/></label><label>Your architecture (optional)<textarea rows="6" value={candidate} onChange={e=>setCandidate(e.target.value)} placeholder="Describe your design for feedback on your own choices instead of the AI reference."/></label><button disabled={loading||prompt.trim().length<10} onClick={generate}>{loading?'Working…':'Generate architecture reference'}</button></div>
      {design&&<><div className="panel"><h2>Reference architecture</h2><p>{design.architecture.summary}</p><Diagram source={design.architecture.diagram}/><div className="columns"><Details title="Services" items={design.architecture.services}/><Details title="Databases" items={design.architecture.databases}/><Details title="Caching" items={design.architecture.caching}/><Details title="APIs" items={design.architecture.apis}/><Details title="Trade-offs" items={design.architecture.tradeoffs}/><Details title="Assumptions" items={design.architecture.assumptions}/></div><h3>Scaling strategy</h3><p>{design.architecture.scaling_strategy}</p><button disabled={loading} onClick={review}>Review {design.review_target==='candidate'?'my design':'generated reference'}</button></div>
      {design.review&&<div className="panel"><h2>Design review <span className="tag">{design.review_target}</span></h2><p className="score">{design.score}/10</p><p>{design.review.feedback}</p><div className="columns"><Details title="Strengths" items={design.review.strengths}/><Details title="Risks" items={design.review.risks}/><Details title="Improvements" items={design.review.improvements}/><Details title="Keyword hints (not proof)" items={design.hints}/></div></div>}</>}
    </>}
    <footer>Model-generated feedback is practice guidance, not a hiring assessment. Sessions are stored locally; do not enter private information.</footer>
  </main>;
}
