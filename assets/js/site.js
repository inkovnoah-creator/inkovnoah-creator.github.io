const WHATSAPP_NUMBER = '8619564380551';
const EMAIL_ADDRESS = 'inkovnoah@gmail.com';
const THANK_YOU_URL = 'thank-you.html';

function trackContact(eventName, extra = {}, callback) {
  const payload = Object.assign({ event_category: 'lead', event_label: window.location.pathname || 'website' }, extra);
  let called = false;
  const done = () => { if (called) return; called = true; if (typeof callback === 'function') callback(); };
  if (typeof gtag === 'function') {
    try {
      gtag('event', eventName, Object.assign({}, payload, { event_callback: done, event_timeout: 1200 }));
      setTimeout(done, 1300);
    } catch(e) { done(); }
  } else { done(); }
}

function buildQuoteMessage(form) {
  const get = (name) => (form.querySelector(`[name="${name}"]`) || {}).value || '';
  const isUsaLanding = form.dataset.thankYou === 'true' || /china-to-usa-shipping\.html$/.test(window.location.pathname);
  const firstLine = isUsaLanding
    ? 'Hello HC Freight, I would like a China to USA DDP shipping quote.'
    : 'Hello HC Freight, I would like a shipping quote.';
  return [firstLine,'',`Name: ${get('name')}`,`Contact: ${get('contact')}`,`Destination: ${get('destination')}`,`Preferred service: ${get('method')}`,`Cargo: ${get('cargo')}`,`Details: ${get('details')}`].join('\n');
}
function shouldGoToThankYou(form) { return form.dataset.thankYou === 'true' || /china-to-usa-shipping\.html$/.test(window.location.pathname); }
function goToThankYouPage() { setTimeout(() => { window.location.href = THANK_YOU_URL; }, 600); }
function sendWhatsAppQuote(event) {
  event.preventDefault();
  const form = event.target;
  if (!form.reportValidity()) return;
  const url = `https://wa.me/${WHATSAPP_NUMBER}?text=${encodeURIComponent(buildQuoteMessage(form))}`;
  const formName = form.dataset.formName || 'quote_form';
  const isConversionLanding = shouldGoToThankYou(form);
  const eventName = isConversionLanding ? 'quote_contact_click' : 'quote_whatsapp_submit';
  const extra = isConversionLanding ? { contact_method: 'whatsapp', form_name: formName, page_location: window.location.href, transport_type: 'beacon' } : { contact_method: 'whatsapp', form_name: formName };
  trackContact(eventName, extra, () => { window.open(url, '_blank'); if (isConversionLanding) goToThankYouPage(); });
}
function sendEmailQuote(buttonOrEvent) {
  if (buttonOrEvent && typeof buttonOrEvent.preventDefault === 'function') buttonOrEvent.preventDefault();
  const source = buttonOrEvent && buttonOrEvent.target ? buttonOrEvent.target : buttonOrEvent;
  const form = source && source.closest ? source.closest('form') : null;
  if (!form) return;
  if (!form.reportValidity()) return;
  const isConversionLanding = shouldGoToThankYou(form);
  const subject = isConversionLanding ? 'China to USA DDP Quote Request - HC Freight' : 'Freight Quote Request - HC Freight';
  const body = buildQuoteMessage(form) + '\n\nPlease reply with available shipping options and required documents.\n\nThank you.';
  const mailto = `mailto:${EMAIL_ADDRESS}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
  const formName = form.dataset.formName || 'quote_form';
  const eventName = isConversionLanding ? 'quote_contact_click' : 'quote_email_submit';
  const extra = isConversionLanding ? { contact_method: 'email', form_name: formName, page_location: window.location.href, transport_type: 'beacon' } : { contact_method: 'email', form_name: formName };
  trackContact(eventName, extra, () => { window.location.href = mailto; if (isConversionLanding) goToThankYouPage(); });
}
function openWhatsApp(eventName='whatsapp_click') { trackContact(eventName, { contact_method:'whatsapp' }, () => window.open(`https://wa.me/${WHATSAPP_NUMBER}`, '_blank')); }
function setMethod(method) { document.querySelectorAll('select[name="method"]').forEach(sel => { sel.value = method; }); const q=document.getElementById('quoteForm'); if(q) q.scrollIntoView({behavior:'smooth'}); }
