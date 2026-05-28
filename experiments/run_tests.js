const fs = require('fs');
const path = require('path');

const indexHtmlPath = path.join(__dirname, '..', 'static', 'index.html');
const indexHtml = fs.readFileSync(indexHtmlPath, 'utf8');

// 1. Mock Browser Environment Globals
global.window = { __TEST_MODE__: true };

const mockElement = {
  className: '',
  textContent: '',
  innerHTML: '',
  appendChild: () => {},
  classList: {
    add: function(c) { this.className += ' ' + c; },
    remove: function(c) { this.className = this.className.replace(c, ''); }
  },
  style: {}
};

const results = [];

global.document = {
  addEventListener: () => {},
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
    // Return mockElement only if ID is actually defined in the HTML file
    const hasId = indexHtml.includes(`id="${id}"`) || indexHtml.includes(`id='${id}'`);
    if (!hasId) {
      return null;
    }
    return mockElement;
  },
  createElement: (tag) => {
    return {
      tag,
      className: '',
      textContent: '',
      innerHTML: '',
      appendChild: () => {},
      classList: {
        add: function(c) { this.className += ' ' + c; },
        remove: function(c) { this.className = this.className.replace(c, ''); }
      },
      style: {}
    };
  }
};

// 2. Load and Eval static/app.js
const appJsPath = path.join(__dirname, '..', 'static', 'app.js');
const appCode = fs.readFileSync(appJsPath, 'utf8');
eval(appCode);

// 3. Load and Eval static/tests.js
const testsJsPath = path.join(__dirname, '..', 'static', 'tests.js');
const testsCode = fs.readFileSync(testsJsPath, 'utf8');
eval(testsCode);

// 4. Output Results in Terminal
console.log('\n--- Frontend JS Logic Unit Tests ---');
let hasFailures = false;

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
