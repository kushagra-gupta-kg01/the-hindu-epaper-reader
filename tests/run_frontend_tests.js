const fs = require('fs');
const path = require('path');

const indexHtmlPath = path.join(__dirname, '..', 'static', 'index.html');
const indexHtml = fs.readFileSync(indexHtmlPath, 'utf8');

// Assert that Vercel Speed Insights and Sentry tags exist in index.html
if (!indexHtml.includes('/_vercel/insights/script.js')) {
  console.error("RED PHASE FAILURE: Vercel Speed Insights script tag is missing in index.html");
  process.exit(1);
}
if (!indexHtml.includes('browser.sentry-cdn.com') && !indexHtml.includes('js.sentry-cdn.com')) {
  console.error("RED PHASE FAILURE: Sentry browser SDK CDN tag is missing in index.html");
  process.exit(1);
}

// 1. Mock Browser Environment Globals
global.Sentry = {
  init: function(config) {
    this.config = config;
  },
  captureException: function(err) {
    this.lastException = err;
    this.exceptions = this.exceptions || [];
    this.exceptions.push(err);
  }
};

global.window = {
  __TEST_MODE__: true,
  location: {
    search: '',
    pathname: '/'
  },
  history: {
    pushState: function() {}
  },
  scrollY: 0,
  scrollTo: function() {},
  addEventListener: function() {},
  removeEventListener: function() {},
  Sentry: global.Sentry
};

global.localStorage = {
  store: {},
  getItem: function(key) { return this.store[key] || null; },
  setItem: function(key, val) { this.store[key] = String(val); },
  removeItem: function(key) { delete this.store[key]; },
  clear: function() { this.store = {}; }
};

global.fetch = async () => {
  return {
    ok: true,
    json: async () => ({})
  };
};

global.IntersectionObserver = class IntersectionObserver {
  constructor(callback, options) {}
  observe(target) {}
  unobserve(target) {}
  disconnect() {}
};

const textVidePath = path.join(__dirname, '..', 'static', 'vendor', 'text-vide.js');
const textVideCode = fs.readFileSync(textVidePath, 'utf8');
eval(textVideCode);

global.textVide = textVide.textVide;
global.window.textVide = textVide.textVide;

const elementCache = {};

function createMockElement(id = '') {
  const elObj = {
    id: id,
    className: '',
    _textContent: '',
    _innerHTML: '',
    children: [],
    get textContent() {
      return this._textContent;
    },
    set textContent(val) {
      this._textContent = val;
      this._innerHTML = val;
      if (val === '') {
        this.children.length = 0;
      }
    },
    get innerHTML() {
      return this._innerHTML;
    },
    set innerHTML(val) {
      this._innerHTML = val;
      this._textContent = val.replace(/<[^>]+>/g, '');
      if (val === '') {
        this.children.length = 0;
      }
    },
    appendChild: function(el) {
      this.children.push(el);
      this._innerHTML += (el.innerHTML || el.textContent || '');
      this._textContent += (el.textContent || '');
    },
    classList: {
      add: function(c) {
        const classes = new Set(this._el.className.split(' ').filter(Boolean));
        classes.add(c);
        this._el.className = Array.from(classes).join(' ');
      },
      remove: function(c) {
        const classes = new Set(this._el.className.split(' ').filter(Boolean));
        classes.delete(c);
        this._el.className = Array.from(classes).join(' ');
      },
      contains: function(c) {
        const classes = new Set(this._el.className.split(' ').filter(Boolean));
        return classes.has(c);
      }
    },
    style: {},
    focus: function() {
      global.document.activeElement = this;
    },
    getAttribute: function(name) {
      return this[name] || '';
    },
    setAttribute: function(name, val) {
      this[name] = val;
    },
    removeAttribute: function(name) {
      delete this[name];
    },
    querySelectorAll: function(selector) {
      return [];
    },
    addEventListener: function(event, handler) {
      if (!this.listeners) this.listeners = {};
      if (!this.listeners[event]) this.listeners[event] = [];
      this.listeners[event].push(handler);
      if (event === 'click') {
        this.onclick = handler;
      }
    },
    dispatchEvent: function(eventObj) {
      const event = eventObj.type || eventObj;
      if (this.listeners && this.listeners[event]) {
        this.listeners[event].forEach(cb => cb(eventObj));
      }
    },
    cloneNode: function() {
      const clone = createMockElement(this.id);
      clone.className = this.className;
      clone.textContent = this.textContent;
      clone.innerHTML = this.innerHTML;
      clone.classList._el = clone;
      return clone;
    },
    parentNode: {
      replaceChild: function(newChild, oldChild) {
        // No-op
      }
    },
    querySelector: function(selector) {
      if (selector.startsWith('.')) {
        const className = selector.substring(1);
        const findChild = (el) => {
          if (el.className && el.className.split(' ').includes(className)) {
            return el;
          }
          if (el.children) {
            for (const child of el.children) {
              const found = findChild(child);
              if (found) return found;
            }
          }
          return null;
        };
        return findChild(this);
      }
      if (selector.startsWith('#')) {
        const idName = selector.substring(1);
        const findChild = (el) => {
          if (el.id === idName) {
            return el;
          }
          if (el.children) {
            for (const child of el.children) {
              const found = findChild(child);
              if (found) return found;
            }
          }
          return null;
        };
        return findChild(this);
      }
      return null;
    }
  };
  return elObj;
}

function getMockElement(id) {
  if (!elementCache[id]) {
    const el = createMockElement(id);
    el.classList._el = el;
    elementCache[id] = el;
  }
  return elementCache[id];
}

// Pre-populate document elements that the app queries at load time or expects
getMockElement('date-select');
getMockElement('city-select');
getMockElement('notification-banner');
getMockElement('notification-text');
getMockElement('notification-action-btn');
getMockElement('section-nav-list');
getMockElement('headlines-content');
getMockElement('main-loader');
getMockElement('reader-pane');
getMockElement('reader-progress-bar');
getMockElement('reader-close-btn');
getMockElement('reader-content');
getMockElement('reader-loader');
getMockElement('reader-category');
getMockElement('reader-headline');
getMockElement('reader-byline');
getMockElement('reader-dateline');
getMockElement('reader-body');
getMockElement('ai-picks-section');
getMockElement('ai-status-badge');
getMockElement('ai-trigger-panel');
getMockElement('ai-loading-panel');
getMockElement('ai-ready-panel');
getMockElement('ai-picks-grid');
getMockElement('ai-generate-btn');
getMockElement('ai-limit-group');
getMockElement('bionic-toggle-btn');
getMockElement('bionic-fixation-select');
getMockElement('fixation-control');
getMockElement('reader-toolbar');
getMockElement('gutenberg-subcontrols');

const results = [];

global.document = {
  addEventListener: () => {},
  body: getMockElement('body'),
  documentElement: getMockElement('html'),
  activeElement: null,
  querySelector: (selector) => {
    if (selector.startsWith('#')) {
      return global.document.getElementById(selector.substring(1));
    }
    if (selector.startsWith('.')) {
      const className = selector.substring(1);
      for (const id in elementCache) {
        const el = elementCache[id];
        if (el.className && el.className.split(' ').includes(className)) {
          return el;
        }
      }
      const mockId = 'mock-' + className;
      const el = getMockElement(mockId);
      el.className = className;
      return el;
    }
    return null;
  },
  getElementById: (id) => {
    if (id === 'test-results') {
      return {
        innerHTML: '',
        appendChild: (el) => {
          results.push(el);
        },
        insertBefore: (el, before) => {
          results.unshift(el);
        }
      };
    }
    if (elementCache[id]) {
      return elementCache[id];
    }
    const hasId = indexHtml.includes(`id="${id}"`) || indexHtml.includes(`id='${id}'`);
    if (!hasId) {
      return null;
    }
    return getMockElement(id);
  },
  createElement: (tag) => {
    const el = createMockElement();
    el.tag = tag;
    el.classList._el = el;
    return el;
  },
  querySelectorAll: (selector) => {
    if (selector === '.theme-btn') {
      const btn1 = getMockElement('theme-btn-broadside');
      btn1['data-theme'] = 'theme-broadside';
      const btn2 = getMockElement('theme-btn-folio');
      btn2['data-theme'] = 'theme-folio';
      const btn3 = getMockElement('theme-btn-dispatch');
      btn3['data-theme'] = 'theme-dispatch';
      const btn4 = getMockElement('theme-btn-gutenberg');
      btn4['data-theme'] = 'theme-gutenberg';
      return [btn1, btn2, btn3, btn4];
    }
    if (selector === '#ai-limit-group .ai-limit-btn' || selector === '.ai-limit-btn') {
      const btn1 = getMockElement('ai-limit-btn-10');
      btn1.setAttribute('data-limit', '10');
      btn1.className = 'active';
      const btn2 = getMockElement('ai-limit-btn-20');
      btn2.setAttribute('data-limit', '20');
      btn2.className = '';
      const btn3 = getMockElement('ai-limit-btn-25');
      btn3.setAttribute('data-limit', '25');
      btn3.className = '';
      return [btn1, btn2, btn3];
    }
    if (selector === '#gutenberg-subcontrols .ctrl-btn') {
      const btnIvory = getMockElement('paper-btn-ivory');
      btnIvory.setAttribute('data-paper', 'paper-ivory');
      btnIvory.className = 'active';
      const btnWhite = getMockElement('paper-btn-white');
      btnWhite.setAttribute('data-paper', 'paper-white');
      btnWhite.className = '';
      const btnSepia = getMockElement('paper-btn-sepia');
      btnSepia.setAttribute('data-paper', 'paper-sepia');
      btnSepia.className = '';
      return [btnIvory, btnWhite, btnSepia];
    }
    return [];
  }
};

// 2. Load and Eval static/app.js
const appJsPath = path.join(__dirname, '..', 'static', 'app.js');
let appCode = fs.readFileSync(appJsPath, 'utf8');
appCode = appCode.replace('const state =', 'global.state =');
eval(appCode);

// 3. Load and Eval static/tests.js
const testsJsPath = path.join(__dirname, '..', 'static', 'tests.js');
const testsCode = fs.readFileSync(testsJsPath, 'utf8');
eval(testsCode);

// 4. Output Results in Terminal (called asynchronously)
if (typeof global.window.runAllTests === 'function') {
  global.window.runAllTests().then((failedTests) => {
    console.log('\n--- Frontend JS Logic Unit Tests ---');
    let hasFailures = failedTests > 0;
    
    results.forEach(el => {
      if (el.className && el.className.includes('pass')) {
        console.log(`\x1b[32m✓ ${el.textContent.replace('✓ ', '')}\x1b[0m`);
      } else if (el.className && el.className.includes('fail')) {
        hasFailures = true;
        console.log(`\x1b[31m✗ ${el.innerHTML.replace('✗ ', '')}\x1b[0m`);
      } else if (el.textContent) {
        console.log(`\n\x1b[1m\x1b[36m${el.textContent}\x1b[0m\n`);
      }
    });
    
    console.log('-------------------------------------\n');
    if (hasFailures) {
      process.exit(1);
    } else {
      process.exit(0);
    }
  }).catch((err) => {
    console.error("Error executing frontend unit tests:", err);
    process.exit(1);
  });
} else {
  console.error("runAllTests function not found on window object");
  process.exit(1);
}
