window.onload = init

function init(){
    const btn = document.getElementById("subir");
    const rawCode = document.getElementById("code");
    const language = document.getElementById("language");

    btn.addEventListener("click", (e)=>{
        if(!rawCode.value.trim()) {
            return alert("No puede publicar un código en blanco")
        }
        const data = new FormData()
        data.append("code", str2blob(rawCode.value))
        data.append("lang", language.options[language.selectedIndex].value)
        fetch('/upload', {
            method: "POST",
            body: data
        })
        .then(req => req.json())
        .then(res => {
            if(res.status) return alert(res.msg);
            window.location.href = `${window.location.href}/../momento/${res['code-code']}`
        })
    })
}
const str2blob = txt => new Blob([txt]);