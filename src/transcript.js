export const initialTranscript = { text: '', past: [], future: [] };

export function transcriptReducer(state, action) {
  if (action.type === 'undo') {
    if (!state.past.length) return state;
    return { text: state.past.at(-1), past: state.past.slice(0, -1), future: [state.text, ...state.future] };
  }
  if (action.type === 'redo') {
    if (!state.future.length) return state;
    return { text: state.future[0], past: [...state.past, state.text], future: state.future.slice(1) };
  }
  let text = state.text;
  if (action.type === 'edit') text = action.text;
  if (action.type === 'append') text = [state.text.trim(), action.word.trim()].filter(Boolean).join(' ');
  if (action.type === 'remove') text = state.text.trim().split(/\s+/).slice(0, -1).join(' ');
  if (action.type === 'clear') text = '';
  if (text === state.text) return state;
  return { text, past: [...state.past.slice(-99), state.text], future: [] };
}

export function validSegment(start, end, duration) {
  return Number.isFinite(start) && Number.isFinite(end) && start >= 0 && end > start && end <= duration + 0.05;
}
