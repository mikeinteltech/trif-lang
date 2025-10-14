const vscode = require('vscode');

/**
 * @param {vscode.ExtensionContext} context
 */
function activate(context) {
  const keywords = ['let', 'fn', 'if', 'else', 'while', 'for', 'in', 'return', 'spawn', 'true', 'false', 'null'];
  const provider = vscode.languages.registerCompletionItemProvider('trif', {
    provideCompletionItems() {
      return keywords.map((word) => new vscode.CompletionItem(word, vscode.CompletionItemKind.Keyword));
    }
  }, ...'abcdefghijklmnopqrstuvwxyz'.split(''));

  const hover = vscode.languages.registerHoverProvider('trif', {
    provideHover(document, position) {
      const range = document.getWordRangeAtPosition(position);
      const word = range ? document.getText(range) : '';
      const docs = {
        'spawn': 'Run a function asynchronously on the Trif runtime thread pool.',
        'let': 'Declare a new mutable binding.',
        'fn': 'Define a function block.'
      };
      if (word in docs) {
        return new vscode.Hover(new vscode.MarkdownString(`**${word}**\n\n${docs[word]}`));
      }
      return undefined;
    }
  });

  context.subscriptions.push(provider, hover);
}

function deactivate() {}

module.exports = {
  activate,
  deactivate
};
