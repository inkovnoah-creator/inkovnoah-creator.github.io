const WHATSAPP_NUMBER = '8619564380551';
const EMAIL_ADDRESS = 'inkovnoah@gmail.com';
const THANK_YOU_URL = '/thank-you';

const DEFAULT_WHATSAPP_MESSAGE = 'Hello Noah, I need a shipping quote.';

function getWhatsAppUrl(message = DEFAULT_WHATSAPP_MESSAGE) {
  return `https://wa.me/${WHATSAPP_NUMBER}?text=${encodeURIComponent(message || DEFAULT_WHATSAPP_MESSAGE)}`;
}

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
    } catch (e) {
      done();
    }
  } else {
    done();
  }
}

function buildQuoteMessage(form) {
  const get = (name) => {
    const field = form && form.querySelector ? form.querySelector(`[name="${name}"]`) : null;
    return field && field.value ? field.value.trim() : '';
  };

  return [
    'Hello Noah, I need a shipping quote.',
    '',
    `Name: ${get('name')}`,
    `Contact: ${get('contact')}`,
    `Delivery address: ${get('destination')}`,
    `Preferred service: ${get('method')}`,
    `Cargo: ${get('cargo')}`,
    `Details: ${get('details')}`
  ].join('\n');
}

function hasAnyFormValue(form) {
  if (!form || !form.querySelectorAll) return false;
  return Array.from(form.querySelectorAll('input, textarea, select')).some((field) => {
    return field && field.value && field.value.trim() && field.value.trim() !== 'Not sure yet';
  });
}

function buildSmartQuoteMessage(form) {
  if (!hasAnyFormValue(form)) return DEFAULT_WHATSAPP_MESSAGE;
  return buildQuoteMessage(form);
}

function shouldGoToThankYou(form) {
  return form && form.dataset && form.dataset.thankYou === 'true';
}

function goToThankYouPage() {
  setTimeout(() => {
    window.location.href = THANK_YOU_URL;
  }, 600);
}

function sendWhatsAppQuote(event) {
  if (event && typeof event.preventDefault === 'function') event.preventDefault();

  const source = event && event.target ? event.target : event;
  const form = source && source.closest ? (source.closest('form') || source) : source;

  if (!form || !form.querySelector) {
    openWhatsApp('quote_whatsapp_submit');
    return;
  }

  const formName = form.dataset.formName || 'quote_form';
  const isConversionLanding = shouldGoToThankYou(form);
  const eventName = isConversionLanding ? 'quote_contact_click' : 'quote_whatsapp_submit';
  const extra = isConversionLanding
    ? { contact_method: 'whatsapp', form_name: formName, page_location: window.location.href, transport_type: 'beacon' }
    : { contact_method: 'whatsapp', form_name: formName };

  const url = getWhatsAppUrl(buildSmartQuoteMessage(form));
  trackContact(eventName, extra, () => {
    window.open(url, '_blank');
    if (isConversionLanding) goToThankYouPage();
  });
}

function sendEmailQuote(buttonOrEvent) {
  if (buttonOrEvent && typeof buttonOrEvent.preventDefault === 'function') buttonOrEvent.preventDefault();

  const source = buttonOrEvent && buttonOrEvent.target ? buttonOrEvent.target : buttonOrEvent;
  const form = source && source.closest ? source.closest('form') : null;

  if (!form) return;
  if (!form.reportValidity()) return;

  const isConversionLanding = shouldGoToThankYou(form);
  const subject = isConversionLanding ? 'DDP Door-to-Door Shipping Quote - HC Freight' : 'Freight Quote Request - HC Freight';
  const body = buildQuoteMessage(form) + '\n\nPlease reply with available shipping options and required documents.\n\nThank you.';
  const mailto = `mailto:${EMAIL_ADDRESS}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
  const formName = form.dataset.formName || 'quote_form';
  const eventName = isConversionLanding ? 'quote_contact_click' : 'quote_email_submit';
  const extra = isConversionLanding
    ? { contact_method: 'email', form_name: formName, page_location: window.location.href, transport_type: 'beacon' }
    : { contact_method: 'email', form_name: formName };

  trackContact(eventName, extra, () => {
    window.location.href = mailto;
    if (isConversionLanding) goToThankYouPage();
  });
}

function openWhatsApp(eventName = 'whatsapp_click', message = DEFAULT_WHATSAPP_MESSAGE) {
  trackContact(eventName, { contact_method: 'whatsapp' }, () => {
    window.open(getWhatsAppUrl(message), '_blank');
  });
}

function setMethod(method) {
  document.querySelectorAll('select[name="method"]').forEach((sel) => {
    sel.value = method;
  });
  const q = document.getElementById('quoteForm');
  if (q) q.scrollIntoView({ behavior: 'smooth' });
}

function makeDirectWhatsAppLink(link, options = {}) {
  if (!link) return;

  const eventName = options.eventName || 'direct_whatsapp_quote_click';
  const message = options.message || DEFAULT_WHATSAPP_MESSAGE;
  const label = options.label;

  link.href = getWhatsAppUrl(message);
  link.target = '_blank';
  link.rel = 'noopener';
  link.removeAttribute('onclick');
  if (label) link.textContent = label;

  link.addEventListener('click', (event) => {
    event.preventDefault();
    openWhatsApp(eventName, message);
  });
}

function improveWhatsAppEntryPoints() {
  // Let the WhatsApp form button open WhatsApp even when the visitor has not filled every required field.
  document.querySelectorAll('form[onsubmit*="sendWhatsAppQuote"]').forEach((form) => {
    form.noValidate = true;
  });

  // Main quote buttons: make the first action direct WhatsApp instead of jumping down to the form.
  document.querySelectorAll('a[href="#quoteForm"]').forEach((link) => {
    const isMobileBar = !!link.closest('.mobile-bar');
    makeDirectWhatsAppLink(link, {
      eventName: isMobileBar ? 'mobile_quick_quote_whatsapp_click' : 'quick_quote_whatsapp_click',
      label: isMobileBar ? 'WhatsApp Quote' : 'Get Quote on WhatsApp'
    });
  });

  // Service-specific quote buttons: open WhatsApp directly with the preferred service in the message.
  document.querySelectorAll('a[onclick*="setMethod"]').forEach((link) => {
    const oldOnclick = link.getAttribute('onclick') || '';
    const match = oldOnclick.match(/setMethod\('([^']+)'\)/);
    const method = match ? match[1] : '';
    const message = method
      ? `${DEFAULT_WHATSAPP_MESSAGE}\nPreferred service: ${method}`
      : DEFAULT_WHATSAPP_MESSAGE;

    makeDirectWhatsAppLink(link, {
      eventName: 'service_quote_whatsapp_click',
      label: 'Quote on WhatsApp',
      message
    });
  });
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', improveWhatsAppEntryPoints);
} else {
  improveWhatsAppEntryPoints();
}
