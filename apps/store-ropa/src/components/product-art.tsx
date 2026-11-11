export default function ProductArt({id,food=false}:{id:string;food?:boolean}) {
  const seed=[...id].reduce((sum,c)=>sum+c.charCodeAt(0),0);
  const colors=['#c4b7a3','#495e50','#b5c4d0','#d2a58e','#a5a78a','#e0cfb9'];const color=colors[seed%colors.length];
  return <svg viewBox="0 0 400 420" role="img" aria-label={food?'Ilustração de embalagem fictícia':'Ilustração da peça, meramente representativa'} className="product-art">
    <ellipse cx="200" cy="348" rx="105" ry="12" fill="#35332c" opacity=".09"/>
    {food?<><path d="M139 109h122l13 220H126z" fill={color}/><path d="M139 109h122v21H139z" fill="#eee5d4"/><path d="M135 190h132v102H129z" fill="#faf6ec"/><circle cx="200" cy="232" r="24" fill="#536a44"/><path d="M186 238q27-38 33-12q-12 23-33 12" fill="#cad0a5"/><text x="200" y="274" textAnchor="middle" fontSize="10" letterSpacing="3" fill="#536a44">DA DESPENSA</text></>:id.includes('calca')?<><path d="M139 102h122l18 231h-64l-15-145-15 145h-64z" fill={color}/><path d="M141 123h117M200 126v62" fill="none" stroke="#fff" opacity=".35" strokeWidth="2"/></>:<><path d="M151 107l-63 38 32 66 31-18v132h98V193l31 18 32-66-63-38-29 16h-40z" fill={color}/><path d="M177 111q23 38 46 0M151 139v54M249 139v54" fill="none" stroke="#fff" opacity=".4" strokeWidth="3"/></>}
  </svg>;
}
