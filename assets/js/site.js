const WHATSAPP_NUMBER = '8619564380551';
const EMAIL_ADDRESS = 'inkovnoah@gmail.com';
const DEFAULT_WHATSAPP_MESSAGE = 'Hello Noah, I need a shipping quote.';

function trackContact(eventName, extra = {}, callback) {
  const payload = Object.assign({
    event_category: 'lead',
    event_label: window.location.pathname || 'website'
  }, extra);
  let called = false;
  const done = () => {
    if (called) return;
    called = true;
    if (typeof callback === 'function') callback();
  };
  if (typeof gtag === 'function') {
    try {
      gtag('event', eventName, Object.assign({}, payload, {
        event_callback: done,
        event_timeout: 1200
      }));
      setTimeout(done, 1300);
    } catch(e) { done(); }
  } else {
    done();
  }
}

function whatsappUrl(message = DEFAULT_WHATSAPP_MESSAGE) {
  return `https://wa.me/${WHATSAPP_NUMBER}?text=${encodeURIComponent(message)}`;
}

function openWhatsApp(eventName='whatsapp_click', message=DEFAULT_WHATSAPP_MESSAGE) {
  trackContact(eventName, { contact_method:'whatsapp' }, () => window.open(whatsappUrl(message), '_blank'));
}

function buildQuoteMessage(form) {
  const get = (name) => (form.querySelector(`[name="${name}"]`) || {}).value || '';
  const pageTitle = document.title || 'DoorHC';
  const firstLine = `Hello Noah, I need a shipping quote.`;
  return [
    firstLine,
    '',
    `Page: ${pageTitle}`,
    `Name: ${get('name')}`,
    `Contact: ${get('contact')}`,
    `Destination: ${get('destination')}`,
    `Preferred service: ${get('method')}`,
    `Cargo: ${get('cargo')}`,
    `Details: ${get('details')}`
  ].join('\n');
}

function sendWhatsAppQuote(event) {
  event.preventDefault();
  const form = event.target;
  const message = buildQuoteMessage(form);
  const formName = form.dataset.formName || 'quote_form';
  trackContact('quote_whatsapp_submit', { contact_method:'whatsapp', form_name: formName }, () => {
    window.open(whatsappUrl(message), '_blank');
  });
}

function sendEmailQuote(buttonOrEvent) {
  if (buttonOrEvent && typeof buttonOrEvent.preventDefault === 'function') buttonOrEvent.preventDefault();
  const source = buttonOrEvent && buttonOrEvent.target ? buttonOrEvent.target : buttonOrEvent;
  const form = source && source.closest ? source.closest('form') : null;
  if (!form) return;
  if (!form.reportValidity()) return;
  const subject = 'Shipping Quote Request - DoorHC';
  const body = buildQuoteMessage(form) + '\n\nPlease reply with available shipping options and required documents.\n\nThank you.';
  const mailto = `mailto:${EMAIL_ADDRESS}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
  const formName = form.dataset.formName || 'quote_form';
  trackContact('quote_email_submit', { contact_method:'email', form_name: formName }, () => {
    window.location.href = mailto;
  });
}

function setMethod(method) {
  document.querySelectorAll('select[name="method"]').forEach(sel => { sel.value = method; });
  openWhatsApp('quick_quote_whatsapp', DEFAULT_WHATSAPP_MESSAGE);
}