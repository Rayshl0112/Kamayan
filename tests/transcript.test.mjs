import test from 'node:test';
import assert from 'node:assert/strict';
import { initialTranscript, transcriptReducer, validSegment } from '../src/transcript.js';

test('confirmed signs append in order; rejected predictions do not mutate transcript', () => {
  let state = transcriptReducer(initialTranscript, { type: 'append', word: 'help' });
  state = transcriptReducer(state, { type: 'append', word: 'student' });
  assert.equal(state.text, 'help student');
  assert.deepEqual(transcriptReducer(state, { type: 'reject' }), state);
});

test('manual editing, removal, clear, undo, redo preserve the actual text', () => {
  let state = transcriptReducer(initialTranscript, { type: 'edit', text: 'Please help me' });
  state = transcriptReducer(state, { type: 'remove' });
  assert.equal(state.text, 'Please help');
  state = transcriptReducer(state, { type: 'undo' });
  assert.equal(state.text, 'Please help me');
  state = transcriptReducer(state, { type: 'redo' });
  assert.equal(state.text, 'Please help');
  state = transcriptReducer(state, { type: 'clear' });
  assert.equal(state.text, '');
  assert.equal(transcriptReducer(state, { type: 'undo' }).text, 'Please help');
});

test('a new edit after undo discards redo and empty additions are harmless', () => {
  let state = transcriptReducer(initialTranscript, { type: 'append', word: 'water' });
  state = transcriptReducer(state, { type: 'undo' });
  state = transcriptReducer(state, { type: 'append', word: 'drink' });
  assert.deepEqual(state.future, []);
  assert.equal(transcriptReducer(state, { type: 'append', word: '  ' }).text, 'drink');
});

test('segment bounds prevent empty, reversed, non-finite and out-of-video inputs', () => {
  assert.equal(validSegment(0, 4, 5), true);
  for (const [start, end] of [[1,1], [3,2], [-1,2], [0,7], [NaN,2]]) {
    assert.equal(validSegment(start,end,5), false);
  }
});
