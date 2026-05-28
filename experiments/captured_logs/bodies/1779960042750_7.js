
    var thgpiClientdevice = {
           "xlarge":"(min-width: 1600px)",
           "large":"(min-width: 1024px) and (max-width: 1599px)",
           "small":"(max-width: 767px)",
           "medium":"(min-width: 768px) and (max-width: 1023px)"
   };
   var thgpia = {
           isMobile: false,
           isTablet: false,
           isDesktop: false,
           isLargeDesktop:false
   };
   for ( var type in thgpiClientdevice) {
       if (window.matchMedia(thgpiClientdevice[type]).matches) {
           switch (type) {
           case "xlarge":
               thgpia.isLargeDesktop=true;
               break;
           case "large":
               thgpia.isDesktop=true;
               break;
           case "medium":
               thgpia.isTablet=true;
               break;
           case "small":
               thgpia.isMobile=true;
               break;
           }
           break;
       }
   }
   function thgpiplatform(){
       var Platform = thgpia.isMobile == true ? 'MWEB' : 'WEB';		
       return  Platform;
   }
   function thgpicreateCookie(name,value,days) { if (days) {
        var date = new Date();
        date.setTime(date.getTime()+(days*24*60*60*1000));
        var expires = "; expires="+date.toGMTString();
        }
        else var expires = "";
        document.cookie = name+"="+value+expires+"; path=/";
    }
    function thgpireadCookie(name) {
        var nameEQ = name + "=";
        var ca = document.cookie.split(';');
        for(var i=0;i < ca.length;i++) {
        var c = ca[i];
        while (c.charAt(0)==' ') c = c.substring(1,c.length);
        if (c.indexOf(nameEQ) == 0) return c.substring(nameEQ.length,c.length);
        }
        return null;
    }
    var thgpiuserplandetails ={"term":'',"resource":'',"packCurrency":'',"packValue":'',"packName" :'',"planDuration" : '',"recurring":false,"paymentmode":''}
				
   var dataLayer =  window.dataLayer || [];
function sendErrorEmail(e){var n=new Headers;n.append("Content-Type","application/json");var o=JSON.stringify({body:e.name+" "+e.message});fetch("https://8a1bv15sqc.execute-api.ap-south-1.amazonaws.com/default/sendEmail",{method:"POST",headers:n,body:o,redirect:"follow"}).then(function(e){return e.text()}).then(function(e){console.log(e)}).catch(function(e){console.log("error",e)})}
   
   
   
 (function () {
    tp = window["tp"] || [];

    /* Checkout related */
    /**
     * Event properties
     *
     * chargeAmount - amount of purchase
     * chargeCurrency
     * uid
     * email
     * expires
     * rid
     * startedAt
     * termConversionId
     * termId
     * promotionId
     * token_list
     * cookie_domain
     * user_token
     *
     */
     function onCheckoutComplete(conversion) {
        try {
          if(typeof conversion.chargeAmount === "undefined") {
            if(window.location.href.includes('/home/dsubscription/')){
                    window.location.href = window.location.href.replace('/home/dsubscription/','/reader');
              }
          }
          document.getElementsByClassName("tp-close").length > 0 ? document.getElementsByClassName("tp-close")[0].style.display="none" : null;
 var ud =  '';
         var thgpaymentMode = '';
          try {
          ud = typeof thgpireadCookie === "function" ? (thgpireadCookie("thgpiuserplandetailscook") != null ? JSON.parse(thgpireadCookie("thgpiuserplandetailscook")): '') : '';
              thgpaymentMode = typeof thgpireadCookie === "function" ? (thgpireadCookie("thgpipaymentMode") != null ? thgpireadCookie("thgpipaymentMode"): '') : '';
    } catch (e) {
         
    }
             var dataLayer =  window.dataLayer || [];
             if(typeof conversion.type !="undefined" && conversion.type === "payment") {
                var paymentData ={};
                if(typeof conversion.uid !="undefined"){
                    paymentData['uid'] = conversion.uid;
                }
                if(typeof conversion.email !="undefined"){
                    paymentData['email'] = conversion.email;
                }
                if(typeof conversion.startedAt !="undefined"){
                    paymentData['subscriptionStartDate'] = new Date(conversion.startedAt).toISOString();
                }
                if(typeof conversion.expires !="undefined"){
                    paymentData['subscriptionEndDate'] = new Date(conversion.expires* 1000).toISOString();
                }
                if(typeof conversion.chargeCurrency !="undefined"){
                    paymentData['packCurrency'] = conversion.chargeCurrency;
                }
                if(typeof conversion.rid !="undefined"){
                    paymentData['resource'] = conversion.rid;
                }
                if(typeof conversion.termId !="undefined"){
                    paymentData['term'] = conversion.termId;
                }
                if(typeof conversion.chargeAmount !="undefined"){
                    paymentData['packValue'] = conversion.chargeAmount.toString();
                }
                if(typeof conversion.promotionId !="undefined"){
                    paymentData['promotionApplied'] = conversion.promotionId != null ? true :false;
                }
                paymentData['planDuration'] = typeof ud.planDuration != "undefined" ? ud.planDuration : '';
                paymentData['packName'] = typeof ud.packName != "undefined" ? ud.packName : '';
                paymentData['paymentSelected'] = typeof thgpaymentMode != "undefined"  ? thgpaymentMode : '';
                paymentData['autoRenew'] = (typeof ud.recurring != "undefined" && ud.recurring == true) ? true :false;
                paymentData['platform'] = thgpiplatform();
                var amount = typeof conversion.chargeAmount !="undefined" ? conversion.chargeAmount : 0;
				if(typeof conversion.chargeCurrency !="undefined" && conversion.chargeCurrency.toLowerCase() == "usd"){
                  amount = amount * 79;
                }
               if(thgpaymentMode != "inbaf" && thgpaymentMode != "inbas"){
               dataLayer.push({ "ecommerce": null }); 
              dataLayer.push({
                "event":"charged",
                "transactionId":typeof conversion.termConversionId !="undefined" ? conversion.termConversionId : "notransaction",
                "transactionTotal":amount,
                "transactionProducts": [{
                    "sku": typeof conversion.termId !="undefined" ? conversion.termId : "nosku",
                    "name": typeof ud.packName != "undefined" ? ud.packName : 'noPackname',
                    "category": typeof conversion.rid !="undefined" ? conversion.rid : 'noCategory',
                    "price": amount,
                    "quantity": 1
                    }],
                "data": paymentData,
                "ecommerce": {
                "transaction_id": typeof conversion.termConversionId !="undefined" ? conversion.termConversionId : "notransaction",
                "value":  typeof conversion.chargeAmount !="undefined" ? conversion.chargeAmount : 0,
                "currency": typeof conversion.chargeCurrency != "undefined" ? conversion.chargeCurrency : '',
                "coupon": typeof conversion.promotionId !="undefined" ? conversion.promotionId : "",
                "items": [
                    {
                    "item_id":  typeof conversion.termId !="undefined" ? conversion.termId : "noitemid",
                    "item_name": typeof ud.packName != "undefined" ? ud.packName : 'noPackname',
                    "coupon": typeof conversion.promotionId !="undefined" ? conversion.promotionId : "",
                    "price":  typeof conversion.chargeAmount !="undefined" ? conversion.chargeAmount : 0,
                    "quantity": 1
                    }
                  ]
                }
              });
               }
               if (window.webkit){
				window.webkit.messageHandlers.doStuffMessageHandler.postMessage({payment_success:"true"});
            }
            }
            else{
                var FTData ={};
                if(typeof conversion.uid !="undefined"){
                    FTData['uid'] = conversion.uid;
                }
                if(typeof conversion.email !="undefined"){
                    FTData['email'] = conversion.email;
                }
                if(typeof conversion.startedAt !="undefined"){
                    FTData['subscriptionStartDate'] = new Date(conversion.startedAt).toISOString();
                }
                if(typeof conversion.expires !="undefined"){
                    FTData['subscriptionEndDate'] = new Date(conversion.expires* 1000).toISOString();
                }
                FTData['platform'] = thgpiplatform();
                dataLayer.push({
                    "event":"freetrial_activated",
                    "data": FTData
                });

            }
          updateprofile(conversion)
          } catch(e) {sendErrorEmail(e);
                  console.error(e);
      }
        if(typeof Android != "undefined" && location.pathname == "/appwebview/android/webview.html"){		
            Android.PaymentSuccess();
        }
if(typeof conversion.type !="undefined" && conversion.type === "payment"){
      try {  
      var dataLayer = window.dataLayer = window.dataLayer || [];
        dataLayer.push({
        "event":"PurchaseSuccess",
        "purchaseDetails": {
        "rid":conversion.rid,
        "chargeAmount":conversion.chargeAmount,
        "chargeCurrency":conversion.chargeCurrency,
        "termConversionId":conversion.termConversionId,
        "termId":conversion.termId,
        "uid":conversion.uid
        }
		});}
		 catch(e) {
			 console.error(e);
		 }
    }
    }
    function onCheckoutExternalEvent() {
    }

    function onCheckoutClose(event) {
        /* Default behavior is to refresh the page on successful checkout */
        switch (event.state) {
            case 'checkoutCompleted':
                if (typeof Android != "undefined") {Android.close();}
                break;
            case 'alreadyHasAccess':
                if (typeof Android != "undefined") {Android.close();}
                break;
            case 'close':
                if (typeof Android != "undefined") {Android.close();}
        }
        if (event && event.state == "checkoutCompleted") {
          if(typeof JSBridge !="undefined"){JSBridge.showMessageInNative("success")}
           if(window.location.pathname == "/appwebview/freetrial"){
			
              if (window.webkit){
				window.webkit.messageHandlers.doStuffMessageHandler.postMessage({Free_trial_activated:"true"});
            }
			}else{
			if (window.webkit){
				window.webkit.messageHandlers.doStuffMessageHandler.postMessage({payment_success:"true"});
            }
              location.reload();
            }
        }
    }

    function onCheckoutCancel() {
    }

    function onCheckoutError() {
    }

    function onCheckoutSubmitPayment() {
    }

    /* Meter callback */
    function onMeterExpired() {

    }

    /* Meter callback */
    function onMeterActive() {

    }

    /* Callback executed when a user must login */
    function onLoginRequired() {
        // this is a reference implementation only
        // your own custom login/registration implementation would
        // need to return the tinypass-compatible userRef inside the callback

        // mysite.showLoginRegistration(function (tinypassUserRef)
        // tp.push(["setUserRef", tinypassUserRef]); // tp.offer.startCheckout(params); // }
        // this will prevent the tinypass error screen from displaying

        return false;
    }

    /* Callback executed after a tinypassAccounts login */
    function onLoginSuccess(data) {
        if(data.registration){  
            dataLayer.push({
                              "event":"signup_successful",
                              "data": { 
                                  "email":data.params.email,
                                  "uid":data.params.uid,
                                  "platform":thgpiplatform()
                              } 
                          });
        
          }
          else{
           if(data.params.confirmed === true){
              dataLayer.push({
                              "event":"login_successful",
                              "data": { 
                                  "email":data.params.email,
                                  "uid":data.params.uid,
                                  "platform":thgpiplatform()
                              } 
                          });
              
            }
          }
    }

    /* Callback executed after an experience executed successfully */
    function onExperienceExecute(event) {
    }

    /* Callback executed if experience execution has been failed */
    function onExperienceExecutionFailed(event) {
    }

    /* Callback executed if external checkout has been completed successfully */
    function onExternalCheckoutComplete(event) {
        /* Default behavior is to refresh the page on successful checkout */
        location.reload();
    }
    function onCheckoutStateChange(stateView){
        switch (stateView.stateName) {
			case 'state1': case 'offer':
                    dataLayer.push({
                        "event":"plan_shown"
                    });
				break;				
			case 'state2':
				try {
                    var thgpiuserplandetailscook ={"term":stateView.term.termId,"resource":stateView.term.resource.rid,"packCurrency":stateView.term.chargeCurrency,"packValue":stateView.term.chargeAmount.toString(),"packName" : stateView.term.name,"planDuration" : stateView.term.firstPeriod,"recurring":stateView.term.forceAutoRenew}
					thgpicreateCookie("thgpiuserplandetailscook",JSON.stringify(thgpiuserplandetailscook),0.2);
					thgpiuserplandetails.term = stateView.term.termId;
                    thgpiuserplandetails.resource=stateView.term.resource.rid;
                    thgpiuserplandetails.packCurrency=stateView.term.chargeCurrency;
                    thgpiuserplandetails.packValue=stateView.term.chargeAmount.toString();
                    thgpiuserplandetails.packName=stateView.term.name;
                    thgpiuserplandetails.planDuration= stateView.term.firstPeriod;
                    thgpiuserplandetails.recurring=stateView.term.forceAutoRenew;
					
                   dataLayer.push({ "ecommerce": null }); 
                    dataLayer.push({
                    "event":"plan_selected",
                    "data": { 
                    "planDuration":stateView.term.firstPeriod,
                    "email":tp.pianoId.getUser() != null ? tp.pianoId.getUser().email : '',
                    "uid":tp.pianoId.getUser() != null ? tp.pianoId.getUser().uid : '',
                    "packValue":stateView.term.chargeAmount.toString(),
                    "packName":stateView.term.name,
                    "packCurrency":stateView.term.chargeCurrency,
                    "resource":stateView.term.resource.rid,
                    "term":stateView.term.termId,
                    "platform":thgpiplatform()
                    },
                    "ecommerce": {
                    "value": stateView.term.chargeAmount,
                    "currency": stateView.term.chargeCurrency,
                    "items": [
                    {
                    "item_id":  stateView.term.termId,
                    "item_name": stateView.term.name,
                    "price": stateView.term.chargeAmount,
                    "quantity": 1
                    }
                    ]
                    } 
                    });
				 } catch(e) {
					 console.error(e);
				 }
				break;
		}

       }
       function onCustomEvent(event){
       if(typeof event.eventName !="undefined" && event.eventName == "paytm-email"){
                 var email = '';
          var termId = '';
          var amount = '';
            	var params;
            	var iframeId;
         		 params = JSON.parse(event.params.params);
         		   iframeId = params.iframeId;
                if ((typeof event.params.email != 'undefined') && (event.params.email.length > 0)) {
                    email = event.params.email;
                }
         		if ((typeof event.params.termid != 'undefined') && (event.params.termid.length > 0)) {
                    termId = event.params.termid;
                }
          	if ((typeof event.params.amount != 'undefined') && (event.params.amount.length > 0)) {
                    amount = event.params.amount;
                }
				if(!checkEmail(email)){
                  sendPostMessageToPiano(iframeId, false, 'You have entered an invalid email', 'email');
                }
				else{
                 dataLayer.push({
                "event":"complete_transaction",
                "data": { 
                    "email":email,
                    "packValue":amount,
                    "term":termId,       
                    "platform":thgpiplatform()
                } 
            });
                  location.href =  event.params.paymentlink;
                }
        }
        else if(typeof event.eventName !="undefined" && event.eventName == "paymentselect"){
                if(event.params.paymentmethod == 'pay_u_india_cc'){thgpiuserplandetails.paymentmode="Debit/Credit Card";}
				else if(event.params.paymentmethod == 'pay_u_india_nb'){thgpiuserplandetails.paymentmode="Net Banking"}
				else if(event.params.paymentmethod == 'pay_u_india_upi'){thgpiuserplandetails.paymentmode="UPI"}
				else if(typeof event.params.paymentmethod !='undefined' && event.params.paymentmethod !=''){thgpiuserplandetails.paymentmode=event.params.paymentmethod}
            }
            try {
                if(thgpiuserplandetails.paymentmode !=''){
                thgpicreateCookie("thgpipaymentMode",thgpiuserplandetails.paymentmode,0.2);
				   dataLayer.push({ "ecommerce": null }); 
                dataLayer.push({
                  "event":"payment_selected",
                  "data": { 
                      "planDuration":thgpiuserplandetails.planDuration,
                      "email":tp.pianoId.getUser() != null ? tp.pianoId.getUser().email : '',
                      "uid":tp.pianoId.getUser() != null ? tp.pianoId.getUser().uid : '',
                      "packValue":thgpiuserplandetails.packValue,
                      "packName":thgpiuserplandetails.packName,
                      "packCurrency":thgpiuserplandetails.packCurrency,
                      "resource":thgpiuserplandetails.resource,
                      "term":thgpiuserplandetails.term,
                      "paymentSelected":thgpiuserplandetails.paymentmode,             
                      "platform":thgpiplatform()
                  },
                  "ecommerce": {
                    "value": thgpiuserplandetails.packValue,
                    "currency": thgpiuserplandetails.packCurrency,
                    "payment_type":thgpiuserplandetails.paymentmode,
                    "items": [
                        {
                        "item_id":  thgpiuserplandetails.term,
                        "item_name": thgpiuserplandetails.packName,
                        "price": thgpiuserplandetails.packValue,
                        "quantity": 1
                        }
                     ]
                    }  
                });
                }
				 } catch(e) {
					 console.error(e);
				 }
         
         typeof __thg_event != "undefined" ? __thg_event.triggercustomEvent(event): null;
       }
       function onSubmitPayment(data){
						
        try {
            if(typeof data.term.chargeAmount != "undefined" && data.term.chargeCurrency != null) {
                dataLayer.push({
                "event":"complete_transaction",
                "data": { 
                    "planDuration":data.term.firstPeriod,
                    "email":tp.pianoId.getUser() != null ? tp.pianoId.getUser().email : '',
                    "uid":tp.pianoId.getUser() != null ? tp.pianoId.getUser().uid : '',
                    "packValue":data.term.chargeAmount.toString(),
                    "packName":data.term.name,
                    "packCurrency":data.term.chargeCurrency,
                    "resource":data.term.resource.rid,
                    "term":data.term.termId,
                    "paymentSelected":thgpiuserplandetails.paymentmode,    
                    "autoRenew":data.term.forceAutoRenew,         
                    "platform":thgpiplatform()
                } 
            });
            }
            
        } catch(e) {
                console.error(e);
        }
       }

    tp.push(["setAid", 'zUShAI0Opu']);
  	//tp.push(["setCxenseSiteId", "1127332816254203331"])
    tp.push(["setCookieDomain", '.epaper.thehindu.com']);
    tp.push(["setDataLayerEnabled", true]);
    tp.push(["setEndpoint", 'https://buy.tinypass.com/api/v3']);
    tp.push(["setUseTinypassAccounts", false ]);
    tp.push(["setUsePianoIdUserProvider", true ]);

    /* checkout related events */
    tp.push(["addHandler", "checkoutComplete", onCheckoutComplete]);
    tp.push(["addHandler", "checkoutClose", onCheckoutClose]);
    tp.push(["addHandler", "checkoutCustomEvent", onCheckoutExternalEvent]);
    tp.push(["addHandler", "checkoutCancel", onCheckoutCancel]);
    tp.push(["addHandler", "checkoutError", onCheckoutError]);
    tp.push(["addHandler", "checkoutSubmitPayment", onCheckoutSubmitPayment]);
    tp.push(["addHandler", "checkoutStateChange", onCheckoutStateChange]);

    /* user login events */
    tp.push(["addHandler", "loginRequired", onLoginRequired]);
    tp.push(["addHandler", "loginSuccess", onLoginSuccess]);

    /* meter related */
    tp.push(["addHandler", "meterExpired", onMeterExpired]);
    tp.push(["addHandler", "meterActive", onMeterActive]);

    tp.push(["addHandler", "experienceExecute", onExperienceExecute]);
    tp.push(["addHandler", "experienceExecutionFailed", onExperienceExecutionFailed]);

    /* external checkout related events */
    tp.push(["addHandler", "externalCheckoutComplete", onExternalCheckoutComplete]);
    tp.push(["addHandler", "customEvent",onCustomEvent]);
    tp.push( [ "addHandler", "submitPayment",onSubmitPayment]);
     //tp.push(['setPianoIdUrl', 'https://auth.thehindugroup.com/']);
    tp.push(["init", function () {
        tp.experience.init()
        if (!tp.user.isUserValid()) {
            var tokenMatch = location.search.match(/reset_token=([A-Za-z0-9]+)/);
            if (tokenMatch) {
                var token = tokenMatch[1];
                tp.pianoId.show({
                    'resetPasswordToken': token
                });
            }
         }
      tp.pianoId.init({
        displayMode: 'modal',
        confirmation:'none',
    profileUpdate: function(data) {
        if (typeof updateprofile == "function") {
           updateprofile(data)
        }
           
    }
});
    }]);
})();


    // do not change this section
    // |BEGIN INCLUDE TINYPASS JS|
     window.onmessage = function(event) {
	if (event.data && event.data.event_id == "mysubscription") {
		var iframeIdUrl = event.data.data.url;
      var iframeId = getUrlParameter("iframeId",iframeIdUrl);
       console.log(getUrlParameter("iframeId===",iframeId))
       tp.api.callApi("/access/list", {cross_app:true,active:false}, function(data) { 
           sendPostMessageToPiano(iframeId, false, 'AccessList', {"data":data,"aid":tp.aid});                                             
       });
    }
  	else if (event.data && event.data.event_id == "myaccount_url") {
      var newUrl = new URL(window.location.href);
		if(typeof event.data.data.name != "undefined"){
			var search_params = newUrl.searchParams;
			search_params.set('tab', event.data.data.name);
          history.pushState({}, null, newUrl.toString());
        }
	
    }
  
  else if (event.data && event.data.event_id == "logout") {
    try {
      const user_sess_ep = "https://epaper.thehindu.com/usersessions";

      const user_sess_req_headers = new Headers();
      user_sess_req_headers.append("Content-Type", "application/json");
      user_sess_req_headers.append("x-client-auth", tp.pianoId.getToken());

      const user_sess_req_options = {
        method: "POST",
        headers: user_sess_req_headers,
        body: JSON.stringify({
          type: "piano",
          session_ids: [
            { [tp.pianoId.getUser().uid]: tp.pianoId.getToken() },
          ],
        }),
      };

      fetch(user_sess_ep, user_sess_req_options)
        .then(function(res) {
        if (!res.ok) {
          console.log("user session request status code: ", res.status);
        }
      })
        .catch(function(err) {
        	console.log(err)
      })
        .finally(function() {
        tp.pianoId.logout()
      });
    } catch (err) {
      console.log("user session request internal error!!", err);
      tp.pianoId.logout();
    }
  }
   else if (event.data && event.data.event_id == "invoice_option_1") {
     location.href = "https://pay.thehindu.com/piano/asyncpayment?aid="+tp.aid+"&return_url="+encodeURIComponent(window.location.href)+"&user_payment_id="+event.data.data.paymentId +  "&term_conversion_id="+event.data.data.termConversionId;
}
  else if (event.data && event.data.event_id == "invoice_option_2") {
  location.href = "https://pay.thehindu.com/piano/asyncpayment/payu?aid="+tp.aid+"&return_url="+encodeURIComponent(window.location.href)+"&user_payment_id="+event.data.data.paymentId +  "&term_conversion_id="+event.data.data.termConversionId;
}
   	else if (event.data && event.data.event_id == "deleteAccount") {
     var iframeIdUrl = event.data.data.url;
      var iframeId = getUrlParameter("iframeId",iframeIdUrl);
      
      var myHeaders = new Headers();
myHeaders.append("Content-Type", "application/json");
      myHeaders.append("x-client-auth", tp.pianoId.getToken());
var raw = JSON.stringify({
  "sourceSystemName": "web",
  "dataSubjectEmail": tp.pianoId.getUser().email,
  "dataSubjectPhone": "",
  "aid":tp.aid,
  "dataSubjectUID": tp.pianoId.getUser().uid,
   "remarks": typeof event.data.data.deleteReason != "undefined" ? event.data.data.deleteReason : "",
  "DSAR_Category": "Right to Erasure"
});
var requestOptions = {
  method: 'POST',
  headers: myHeaders,
  body: raw,
};
  fetch("https://uf.thehindu.com/forgetme", requestOptions).then(function(response) {
    if(response.ok) {
    return response.json();
    }
    }).then(function(result) {
      if(result.code == 0){
          sendPostMessageToPiano(iframeId, false, 'dsarref', {"data":result,"aid":tp.aid});
      }
            else{
              console.log(error);
            }
    
    }).catch(function(error) {
    console.log(error);
    });
    }
};
function getUrlParameter( name, url ) {
if (!url) url = location.href;
name = name.replace(/[\[]/,"\\\[").replace(/[\]]/,"\\\]");
var regexS = "[\\?&]"+name+"=([^&#]*)";
var regex = new RegExp(regexS,"i");
var results = regex.exec( url );
return results == null ? null : results[1];
} 
var currentUrl = window.location.href.split('?')[0];
		var hasHtmlExtension = currentUrl.endsWith(".html");
		if(hasHtmlExtension){
         (function(src){var a=document.createElement("script");a.type="text/javascript";a.async=true;a.src=src;var b=document.getElementsByTagName("script")[0];b.parentNode.insertBefore(a,b)})("//cdn.tinypass.com/api/tinypass.min.js");
        }
    // |END   INCLUDE TINYPASS JS|
function sendPostMessageToPiano(iframeId, success, message, object) {
    var iframe = document.querySelectorAll('#' + iframeId);
    if (iframe.length) {
        iframe[0].contentWindow.postMessage({
            piano: {
                success: success,
                message: message,
                object: object
            }
        }, '*');
    }
}function checkEmail(email){var mailValidation = /^([\w-]+(?:\.[\w-]+)*)@((?:[\w-]+\.)*\w[\w-]{1,66})\.([A-Za-z]{2,6}(?:\.[A-Za-z]{2})?)$/;if(!mailValidation.test(email) ){return false}else{return true}}

function updateprofile(data) {function isBlank(e){return!e||/^\s*$/.test(e)}tp.pianoId.loadExtendedUser({extendedUserLoaded:function(e){if("object"==typeof e.custom_field_values&&e.custom_field_values.length>0){dataLayer=window.dataLayer||[];var a={};e.custom_field_values.forEach(function(e){isBlank(e.value)||(a[e.field_name]=e.value)}),Object.keys(a.length>0)&&dataLayer.push({event:"profile_updated",data:a})}},formName:"MyAccountFields"});}

