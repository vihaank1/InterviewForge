import {useEffect,useState} from 'react';
import mermaid from 'mermaid';
mermaid.initialize({startOnLoad:false,securityLevel:'strict',theme:'dark'});
let count=0;
export default function Diagram({source}){
 const [svg,setSvg]=useState('');const [error,setError]=useState(false);
 useEffect(()=>{let active=true;setSvg('');setError(false);if(!source)return;
 mermaid.render('forge-'+(++count),source).then(({svg})=>{if(active)setSvg(svg)}).catch(()=>{if(active)setError(true)});
 return()=>{active=false};},[source]);
 return error?<pre>{source}</pre>:<div className="diagram">{svg?<div dangerouslySetInnerHTML={{__html:svg}}/>:<p>Rendering architecture…</p>}</div>;
}
