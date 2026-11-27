(function(){
  var diets=[
    {label:"Halal",value:"halal"},
    {label:"Vegetarian",value:"vegetarian"},
    {label:"Vegan",value:"vegan"},
    {label:"Hindu-friendly (no beef)",value:"hindu"},
    {label:"Kosher",value:"kosher"}
  ];
  var allergies=["Peanuts","Milk","Eggs","Gluten","Soy","Tree nuts","Fish","Sesame",
    "Crustacean shellfish","Molluscs","Celery","Mustard","Lupin","Sulphites"];
  var note=document.getElementById("note");
  var file=document.getElementById("file");
  var dropZone=document.getElementById("drop-zone");
  var ingredients=document.getElementById("ing");
  var searchNote=document.getElementById("search-note");
  var preview=document.getElementById("preview");
  var previewDetails=document.getElementById("preview-details");
  var previewEmpty=document.getElementById("preview-empty");
  var processingDialog=document.getElementById("processing-dialog");
  var processingTitle=document.getElementById("processing-title");
  var processingState=document.getElementById("processing-state");
  var resultBox=document.getElementById("result");
  var modeNotice=document.getElementById("mode-notice");
  var previewUrl=null;

  function apiConnectionHelp(){
    if(location.port==="5500"){
      return "VS Code Live Server can't reach FoodLens. Open http://127.0.0.1:5000/ instead.";
    }
    return "Couldn't reach FoodLens. Check your connection and try again.";
  }

  function showProcessing(isPhoto){
    processingTitle.textContent=isPhoto?"Processing your photo":"Checking ingredients";
    processingState.textContent=isPhoto
      ?"Preparing your photo…"
      :"Reviewing ingredients and checking anything unclear…";
    if(!processingDialog.open){
      if(typeof processingDialog.showModal==="function") processingDialog.showModal();
      else processingDialog.setAttribute("open","");
    }
  }

  function hideProcessing(){
    if(processingDialog.open){
      if(typeof processingDialog.close==="function") processingDialog.close();
      else processingDialog.removeAttribute("open");
    }
  }

  document.getElementById("processing-close").addEventListener("click",hideProcessing);

  fetch("/api/mode").then(function(response){
    if(!response.ok) throw new Error("FoodLens API unavailable");
    return response.json();
  }).then(function(mode){
    if(!mode) return;
    if(mode.demo_mode){
      modeNotice.textContent="Demo mode: photo scans use sample ingredients and do not read your photo. Typed ingredient checks use the rules.";
      modeNotice.hidden=false;
    }else if(!mode.photo_scan_available){
      modeNotice.textContent="Photo scanning is not configured on this server. You can still type ingredients.";
      modeNotice.hidden=false;
    }
  }).catch(function(){
    if(location.port==="5500"){
      modeNotice.textContent=apiConnectionHelp();
      modeNotice.hidden=false;
    }
  });

  /* ---------- small safe-DOM helper: text only, never innerHTML ---------- */
  function el(tag,cls,text){
    var node=document.createElement(tag);
    if(cls) node.className=cls;
    if(text!==undefined&&text!==null) node.textContent=text;
    return node;
  }

  function addChips(id,list,cls){
    var box=document.getElementById(id);
    var firstVisible=cls==="al"?5:list.length;
    var moreButton=null;
    var expanded=false;
    function refreshMoreLabel(){
      if(!moreButton) return;
      var selectedExtra=0;
      box.querySelectorAll(".chip-extra").forEach(function(chip){
        if(chip.getAttribute("aria-pressed")==="true") selectedExtra++;
      });
      moreButton.textContent=expanded?"Show less":"More ("+(list.length-firstVisible)+(selectedExtra?", "+selectedExtra+" selected":"")+")";
    }
    list.forEach(function(item,index){
      var button=document.createElement("button");
      button.type="button";
      button.className="chip "+cls;
      if(cls==="al"&&index>=firstVisible){button.classList.add("chip-extra");button.hidden=true;}
      button.textContent=typeof item==="string"?item:item.label;
      if(typeof item!=="string") button.setAttribute("data-value",item.value);
      button.setAttribute("aria-pressed","false");
      button.addEventListener("click",function(){
        if(cls==="di"){
          box.querySelectorAll(".chip").forEach(function(chip){chip.setAttribute("aria-pressed","false");});
          button.setAttribute("aria-pressed","true");
        }else{
          button.setAttribute("aria-pressed",button.getAttribute("aria-pressed")==="true"?"false":"true");
          if(button.classList.contains("chip-extra")) refreshMoreLabel();
        }
      });
      box.appendChild(button);
    });
    if(cls==="al"&&list.length>firstVisible){
      moreButton=document.createElement("button");
      moreButton.type="button";
      moreButton.className="chip-more";
      moreButton.setAttribute("aria-expanded","false");
      moreButton.textContent="More ("+(list.length-firstVisible)+")";
      moreButton.addEventListener("click",function(){
        expanded=!expanded;
        box.querySelectorAll(".chip-extra").forEach(function(chip){chip.hidden=!expanded;});
        moreButton.setAttribute("aria-expanded",expanded?"true":"false");
        refreshMoreLabel();
      });
      box.appendChild(moreButton);
    }
  }

  addChips("diet-options",diets,"di");
  addChips("allergy",allergies,"al");
  document.querySelector("#diet-options .chip").setAttribute("aria-pressed","true");

  function selectTab(tabId){
    document.querySelectorAll(".tab").forEach(function(tab){
      var selected=tab.id===tabId;
      tab.setAttribute("aria-selected",selected?"true":"false");
      document.getElementById(tab.getAttribute("aria-controls")).hidden=!selected;
    });
  }

  document.querySelectorAll(".tab").forEach(function(tab){
    tab.addEventListener("click",function(){selectTab(tab.id);});
  });

  file.addEventListener("change",function(event){
    var selected=event.target.files[0];
    document.getElementById("fname").textContent=selected?"Selected: "+selected.name:"A clear, well-lit photo works best";
    if(previewUrl){URL.revokeObjectURL(previewUrl);previewUrl=null;}
    if(selected){
      previewUrl=URL.createObjectURL(selected);
      preview.src=previewUrl;preview.hidden=false;previewEmpty.hidden=true;previewDetails.open=true;
      note.textContent="Photo ready. Choose your preferences, then check the label.";
    }else{preview.hidden=true;previewEmpty.hidden=false;previewDetails.open=false;preview.removeAttribute("src");}
  });

  dropZone.addEventListener("dragover",function(event){
    event.preventDefault();
    dropZone.classList.add("is-dragover");
  });
  dropZone.addEventListener("dragleave",function(event){
    if(!dropZone.contains(event.relatedTarget)) dropZone.classList.remove("is-dragover");
  });
  dropZone.addEventListener("drop",function(event){
    event.preventDefault();
    dropZone.classList.remove("is-dragover");
    if(!event.dataTransfer||!event.dataTransfer.files.length) return;
    file.files=event.dataTransfer.files;
    file.dispatchEvent(new Event("change",{bubbles:true}));
  });

  document.getElementById("quick-search-form").addEventListener("submit",function(event){
    event.preventDefault();
    var query=document.getElementById("quick-search").value.trim();
    if(!query){
      searchNote.textContent="Type an ingredient or E-number to get started.";
      document.getElementById("quick-search").focus();
      return;
    }
    ingredients.value=query;
    selectTab("t-text");
    searchNote.textContent="Added to your check. Choose your preferences below.";
    document.getElementById("scanner").scrollIntoView({behavior:"smooth",block:"start"});
    window.setTimeout(function(){ingredients.focus({preventScroll:true});},350);
  });

  document.getElementById("camera-shortcut").addEventListener("click",function(){
    selectTab("t-photo");
    document.getElementById("scanner").scrollIntoView({behavior:"smooth",block:"start"});
    file.click();
  });

  document.querySelectorAll(".sample-item").forEach(function(sample){
    sample.addEventListener("click",function(){
      ingredients.value=sample.getAttribute("data-ingredients");
      selectTab("t-text");
      note.textContent="Sample added. Choose your preferences, then check it.";
      document.getElementById("scanner").scrollIntoView({behavior:"smooth",block:"start"});
      window.setTimeout(function(){ingredients.focus({preventScroll:true});},350);
    });
  });

  /* ---------- shrink phone photos so uploads stay small and fast ---------- */
  function prepareImage(source){
    return new Promise(function(resolve,reject){
      var url=URL.createObjectURL(source);
      var img=new Image();
      img.onload=function(){
        URL.revokeObjectURL(url);
        var scale=Math.min(1,1600/Math.max(img.naturalWidth,img.naturalHeight));
        var canvas=document.createElement("canvas");
        canvas.width=Math.max(1,Math.round(img.naturalWidth*scale));
        canvas.height=Math.max(1,Math.round(img.naturalHeight*scale));
        canvas.getContext("2d").drawImage(img,0,0,canvas.width,canvas.height);
        canvas.toBlob(function(blob){
          blob?resolve(blob):reject(new Error("We couldn't prepare that photo. Try another one."));
        },"image/jpeg",0.85);
      };
      img.onerror=function(){
        URL.revokeObjectURL(url);
        reject(new Error("We couldn't read that image. Try a JPG or PNG photo."));
      };
      img.src=url;
    });
  }

  /* ---------- result card ---------- */
  var VERDICT={
    ok:{mark:"✓",title:"Looks suitable",text:"No conflict found in the ingredients we recognised."},
    doubtful:{mark:"?",title:"Needs a closer look",text:"Some ingredients may conflict, or their source isn't stated on the label."},
    not_ok:{mark:"✕",title:"Not suitable for this selection",text:"At least one ingredient conflicts with your choice."},
    unknown:{mark:"i",title:"Not enough information",text:"At least one ingredient remains unconfirmed, so we can't give a reliable answer."}
  };
  var STATUS={ok:"OK",doubtful:"Check",not_ok:"Not OK",unknown:"Unknown"};

  function section(title){return el("h3",null,title);}

  function renderResult(r){
    resultBox.textContent="";
    var v=VERDICT[r.verdict]||VERDICT.unknown;
    var dietLabel=r.diet==="hindu"?"Hindu-friendly (no beef)":r.diet.charAt(0).toUpperCase()+r.diet.slice(1);

    if(r.demo_mode){
      var demo=el("div","alert alert-demo");
      demo.setAttribute("role","note");
      demo.appendChild(el("strong",null,"Demo result"));
      demo.appendChild(el("span",null,"These ingredients are sample data, not text read from your photo."));
      resultBox.appendChild(demo);
    }

    var banner=el("div","verdict v-"+(VERDICT[r.verdict]?r.verdict:"unknown"));
    banner.appendChild(el("span","verdict-mark",v.mark)).setAttribute("aria-hidden","true");
    var head=el("div");
    var title=el("h2",null,v.title);title.id="result-title";
    head.appendChild(title);
    head.appendChild(el("p",null,"Checked for: "+dietLabel+". "+v.text));
    banner.appendChild(head);
    resultBox.appendChild(banner);

    if(r.ai_assisted){
      var aiInfo=el("div","alert alert-ai");
      aiInfo.setAttribute("role","note");
      aiInfo.appendChild(el("strong",null,"AI assessment"));
      aiInfo.appendChild(el("span",null,r.ai_grounded
        ?"The AI checked web sources and gives a screening estimate. It is not product certification or a personal religious ruling."
        :"The AI gave an estimate, but no source links were returned. It is not product certification or a personal religious ruling."));
      resultBox.appendChild(aiInfo);
    }
    if(r.ai_sources&&r.ai_sources.length){
      var sourcesBox=el("div","ai-sources");
      sourcesBox.appendChild(el("strong",null,"Sources used for this AI check"));
      var sourcesList=el("ul");
      r.ai_sources.forEach(function(source){
        if(!source||typeof source.url!=="string"||!/^https?:\/\//i.test(source.url)) return;
        var row=document.createElement("li");
        var link=document.createElement("a");
        link.href=source.url;
        link.target="_blank";
        link.rel="noopener noreferrer";
        link.textContent=source.title||source.url;
        row.appendChild(link);
        sourcesList.appendChild(row);
      });
      if(sourcesList.childNodes.length){
        sourcesBox.appendChild(sourcesList);
        resultBox.appendChild(sourcesBox);
      }
    }
    if(r.ai_check_warning){
      var aiWarning=el("div","alert alert-precaution");
      aiWarning.setAttribute("role","note");
      aiWarning.appendChild(el("strong",null,"Some ingredients still need checking"));
      aiWarning.appendChild(el("span",null,"The AI could not confidently settle every unclear ingredient. Check its source or product certification."));
      resultBox.appendChild(aiWarning);
    }

    if(r.diet==="halal"&&r.verdict==="not_ok"){
      var conflicts=r.items.filter(function(i){return i.status==="not_ok";});
      var ruleConflict=conflicts.some(function(i){return !i.ai_estimated;});
      var halalAlert=el("div",ruleConflict?"alert alert-haram":"alert alert-ai");
      halalAlert.setAttribute("role",ruleConflict?"alert":"note");
      halalAlert.appendChild(el("strong",null,ruleConflict?"Halal rule conflict":"AI screening result"));
      var names=conflicts.map(function(i){return i.ingredient;});
      halalAlert.appendChild(el("span",null,ruleConflict?"Rule-based conflict found: "+names.join(", ")+".":"The AI estimates these ingredients may not fit the Halal profile: "+names.join(", ")+"."));
      resultBox.appendChild(halalAlert);
    }
    if(r.allergy_alerts&&r.allergy_alerts.length){
      var al=el("div","alert alert-allergy");
      al.setAttribute("role","alert");
      al.appendChild(el("strong",null,"Allergy alert"));
      al.appendChild(el("span",null,"Listed as an ingredient and matches your allergies: "+r.allergy_alerts.join(", ")+"."));
      resultBox.appendChild(al);
    }
    if(r.precautionary&&r.precautionary.length){
      var pc=el("div","alert alert-precaution");
      pc.appendChild(el("strong",null,r.precautionary_alerts&&r.precautionary_alerts.length?"Possible traces of your allergens":"Precautionary label statement"));
      r.precautionary.forEach(function(p){
        pc.appendChild(el("span",null,p.text+(p.allergens.length?" ("+p.allergens.join(", ")+")":"")));
        pc.appendChild(document.createElement("br"));
      });
      pc.appendChild(el("span",null,"These are warnings of possible cross-contact, separate from the listed ingredients."));
      resultBox.appendChild(pc);
    }

    resultBox.appendChild(section("Ingredient by ingredient"));
    var list=el("ul","ing-list");
    r.items.forEach(function(item){
      var li=el("li");
      var left=el("div");
      left.appendChild(el("span","ing-name",item.ingredient));
      if(item.note) left.appendChild(el("small",null,item.note.replace(/^Gemini estimate/i,"AI estimate")));
      li.appendChild(left);
      var st=VERDICT[item.status]?item.status:"unknown";
      li.appendChild(el("span","badge b-"+st,STATUS[st]));
      list.appendChild(li);
    });
    resultBox.appendChild(list);

    if(r.allergens&&r.allergens.length){
      resultBox.appendChild(section("Allergens found in the ingredients"));
      resultBox.appendChild(el("p",null,r.allergens.join(", ")));
    }

    if(r.nutrition){
      var nutritionHeading="Nutrition ("+(r.nutrition.basis||"basis not identified")+")";
      if(r.nutrition.basis==="per serving"&&r.nutrition.serving_size_g){
        nutritionHeading="Nutrition (per "+r.nutrition.serving_size_g+" g serving)";
      }
      var dl=el("dl","nutri");
      [["calories","Calories"],["fat_g","Fat (g)"],["carbs_g","Carbs (g)"],["fiber_g","Fiber (g)"],
       ["sugar_g","Sugar (g)"],["protein_g","Protein (g)"],["salt_g","Salt (g)"],["sodium_mg","Sodium (mg)"]].forEach(function(f){
        if(r.nutrition[f[0]]===null||r.nutrition[f[0]]===undefined) return;
        var d=el("div");d.appendChild(el("dt",null,f[1]));d.appendChild(el("dd",null,String(r.nutrition[f[0]])));dl.appendChild(d);
      });
      resultBox.appendChild(section(nutritionHeading));
      resultBox.appendChild(dl);
    }

    resultBox.appendChild(el("p","result-note",
      "Informational only. We can miss text or ingredients, and \"no match\" does not prove a product is allergen-free or certified. "+
      "Check the package, official certification and the manufacturer."+(r.source==="image"?" Photo reading can make mistakes, so compare the list above with your label.":"")));

    var actions=el("div","result-actions");
    var again=el("button","button button-outline","Check another label");
    again.type="button";
    again.addEventListener("click",function(){
      resultBox.hidden=true;
      document.getElementById("scanner").scrollIntoView({behavior:"smooth",block:"start"});
    });
    actions.appendChild(again);
    resultBox.appendChild(actions);

    resultBox.hidden=false;
    resultBox.scrollIntoView({behavior:"smooth",block:"start"});
    resultBox.focus({preventScroll:true});
  }

  /* ---------- recent checks: this device only ---------- */
  var KEY="foodlens.recent";
  function loadRecent(){try{return JSON.parse(localStorage.getItem(KEY))||[];}catch(e){return [];}}
  function saveRecent(list){try{localStorage.setItem(KEY,JSON.stringify(list));}catch(e){}}
  function renderRecent(){
    var list=loadRecent(),box=document.getElementById("recent"),ul=document.getElementById("recent-list");
    ul.textContent="";
    box.hidden=!list.length;
    list.forEach(function(item){
      var li=el("li");
      li.appendChild(el("span",null,item.summary));
      var label=(VERDICT[item.verdict]||VERDICT.unknown).title;
      li.appendChild(el("span","badge b-"+(VERDICT[item.verdict]?item.verdict:"unknown"),label+" · "+item.diet));
      ul.appendChild(li);
    });
  }
  function remember(r){
    var names=r.items.slice(0,3).map(function(i){return i.ingredient;}).join(", ");
    var list=loadRecent();
    list.unshift({summary:(r.source==="image"?"Photo: ":"")+names+(r.items.length>3?"…":""),verdict:r.verdict,diet:r.diet==="hindu"?"Hindu-friendly (no beef)":r.diet});
    saveRecent(list.slice(0,5));
    renderRecent();
  }
  document.getElementById("recent-clear").addEventListener("click",function(){saveRecent([]);renderRecent();});
  renderRecent();

  /* ---------- submit ---------- */
  document.getElementById("go").addEventListener("click",async function(){
    var button=document.getElementById("go");
    var buttonLabel=button.querySelector(".button-label");
    var photo=document.getElementById("t-photo").getAttribute("aria-selected")==="true";
    var formData=new FormData();
    var diet=document.querySelector("#diet-options .chip[aria-pressed=true]");

    if(photo&&!file.files[0]){note.textContent="Add a label photo first.";return;}
    if(!photo&&!ingredients.value.trim()){note.textContent="Type the ingredients first.";ingredients.focus();return;}

    formData.append("diet",diet.getAttribute("data-value"));
    document.querySelectorAll("#allergy .chip[aria-pressed=true]").forEach(function(chip){
      formData.append("allergies",chip.textContent.toLowerCase());
    });

    button.disabled=true;
    button.setAttribute("aria-busy","true");
    button.classList.add("is-loading");
    buttonLabel.textContent=photo?"Reading label…":"Checking ingredients…";
    resultBox.hidden=true;
    showProcessing(photo);
    note.classList.add("note-loading");
    note.textContent=photo
      ?"Reading your label and checking its ingredients. This can take a little while."
      :"Checking ingredients and relevant sources. This can take a little while.";
    try{
      if(photo){
        formData.append("image",await prepareImage(file.files[0]),"label.jpg");
        processingState.textContent="Reading the label and checking its ingredients…";
      }
      else{formData.append("ingredients",ingredients.value.trim());}
      var response,result;
      try{
        response=await fetch("/api/analyze",{method:"POST",body:formData});
        result=await response.json();
      }catch(networkError){
        throw new Error(apiConnectionHelp());
      }
      if(!response.ok){
        var msg=result.error||"The label could not be checked.";
        throw new Error(result.request_id?msg+" (ref "+result.request_id+")":msg);
      }
      hideProcessing();
      note.textContent="";
      renderResult(result);
      remember(result);
    }catch(error){
      note.textContent="Error: "+error.message;
    }finally{
      hideProcessing();
      button.disabled=false;
      button.removeAttribute("aria-busy");
      button.classList.remove("is-loading");
      buttonLabel.textContent="Check this label";
      note.classList.remove("note-loading");
    }
  });
})();
