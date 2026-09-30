async function loadProfile(){
 const d=await fetch("/api/profile").then(r=>r.json());
 document.getElementById("name").value=d.name||"";
 document.getElementById("location").value=d.location||"";
 document.getElementById("email").value=d.email||"";
}
document.getElementById("profileForm")?.addEventListener("submit",async e=>{
 e.preventDefault();
 const fd=new FormData(e.target);
 const r=await fetch("/api/profile",{method:"POST",body:fd});
 const d=await r.json();
 document.getElementById("profileMsg").textContent="Profile saved.";
});
loadProfile();
