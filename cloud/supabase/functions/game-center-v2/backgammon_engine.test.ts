import assert from "node:assert/strict";
import test from "node:test";
import {
  applyBackgammonMove,
  applyTurnSequence,
  countCheckers,
  initialBackgammonState,
  legalMovesForDie,
  legalTurnSequences,
  winnerOf,
  type BackgammonState,
} from "./backgammon_engine.ts";

function emptyState(): BackgammonState {
  return {
    points: Array(24).fill(0),
    bar: { white: 0, black: 0 },
    off: { white: 0, black: 0 },
  };
}

test("standard opening position contains 15 checkers per player", () => {
  const state = initialBackgammonState();
  assert.equal(countCheckers(state, "white"), 15);
  assert.equal(countCheckers(state, "black"), 15);
  assert.equal(state.points[18], 5);
  assert.equal(state.points[5], -5);
});

test("white and black move in opposite directions", () => {
  const state = emptyState();
  state.points[4] = 1;
  state.points[20] = -1;
  assert.deepEqual(legalMovesForDie(state, "white", 2), [
    { from: 4, to: 6, die: 2 },
  ]);
  assert.deepEqual(legalMovesForDie(state, "black", 2), [
    { from: 20, to: 18, die: 2 },
  ]);
});

test("a point occupied by two opposing checkers is blocked", () => {
  const state = emptyState();
  state.points[4] = 1;
  state.points[5] = -2;
  assert.equal(
    legalMovesForDie(state, "white", 1).some((move) => move.from === 4),
    false,
  );
});

test("a blot can be hit and moved to the bar", () => {
  const state = emptyState();
  state.points[4] = 1;
  state.points[5] = -1;
  const next = applyBackgammonMove(state, "white", {
    from: 4,
    to: 5,
    die: 1,
  });
  assert.equal(next.points[5], 1);
  assert.equal(next.bar.black, 1);
  assert.equal(state.points[5], -1, "the original state must remain immutable");
});

test("bar checkers must enter before any board checker moves", () => {
  const state = emptyState();
  state.bar.white = 1;
  state.points[10] = 1;
  assert.deepEqual(legalMovesForDie(state, "white", 3), [
    { from: "bar", to: 2, die: 3 },
  ]);
});

test("a black checker re-enters from the opposite side", () => {
  const state = emptyState();
  state.bar.black = 1;
  assert.deepEqual(legalMovesForDie(state, "black", 3), [
    { from: "bar", to: 21, die: 3 },
  ]);
});

test("a blocked entry point prevents re-entry", () => {
  const state = emptyState();
  state.bar.white = 1;
  state.points[2] = -2;
  assert.deepEqual(legalMovesForDie(state, "white", 3), []);
});

test("bearing off is forbidden until every checker is in the home board", () => {
  const state = emptyState();
  state.points[17] = 1;
  state.points[20] = 1;
  assert.equal(
    legalMovesForDie(state, "white", 4).some((move) => move.to === "off"),
    false,
  );
});

test("a checker can bear off with an exact die", () => {
  const state = emptyState();
  state.points[20] = 1;
  const next = applyBackgammonMove(state, "white", {
    from: 20,
    to: "off",
    die: 4,
  });
  assert.equal(next.off.white, 1);
  assert.equal(next.points[20], 0);
});

test("an oversized die can bear off when no checker is farther from the exit", () => {
  const state = emptyState();
  state.points[20] = 1;
  assert.deepEqual(legalMovesForDie(state, "white", 5), [
    { from: 20, to: "off", die: 5 },
  ]);
});

test("an oversized die cannot skip a checker on a farther home point", () => {
  const state = emptyState();
  state.points[20] = 1;
  state.points[22] = 1;
  const moves = legalMovesForDie(state, "white", 5);
  assert.equal(moves.some((move) => move.from === 20), false);
  assert.equal(moves.some((move) => move.from === 22), true);
});

test("all possible dice must be used when two sequential moves are available", () => {
  const state = emptyState();
  state.points[0] = 1;
  const sequences = legalTurnSequences(state, "white", [1, 2]);
  assert.ok(sequences.length > 0);
  assert.ok(sequences.every((sequence) => sequence.length === 2));
  assert.equal(applyTurnSequence(state, "white", sequences[0]).points[3], 1);
});

test("the higher die is mandatory when only one of two different dice can be used", () => {
  const state = emptyState();
  state.points[20] = 1;
  const sequences = legalTurnSequences(state, "white", [3, 5]);
  assert.ok(sequences.length > 0);
  assert.ok(sequences.every((sequence) => sequence.length === 1));
  assert.ok(sequences.every((sequence) => sequence[0].die === 5));
});

test("doubles grant four moves when all four can be played", () => {
  const state = emptyState();
  state.points[0] = 1;
  const sequences = legalTurnSequences(state, "white", [2, 2, 2, 2]);
  assert.ok(sequences.length > 0);
  assert.ok(sequences.every((sequence) => sequence.length === 4));
});

test("a roll with no legal move returns one empty pass sequence", () => {
  const state = emptyState();
  state.bar.white = 1;
  state.points[0] = -2;
  state.points[1] = -2;
  assert.deepEqual(legalTurnSequences(state, "white", [1, 2]), [[]]);
});

test("invalid die values and malformed board states are rejected", () => {
  const state = emptyState();
  assert.throws(() => legalMovesForDie(state, "white", 0), /die value/);
  assert.throws(
    () => legalMovesForDie({ ...state, points: [0, 1] }, "white", 1),
    /24 points/,
  );
});

test("illegal moves are rejected without changing the source board", () => {
  const state = emptyState();
  state.points[4] = 1;
  state.points[5] = -2;
  assert.throws(
    () => applyBackgammonMove(state, "white", { from: 4, to: 5, die: 1 }),
    /Illegal backgammon move/,
  );
  assert.equal(state.points[4], 1);
  assert.equal(state.points[5], -2);
});

test("winner is declared only after all 15 checkers are borne off", () => {
  const state = emptyState();
  state.off.white = 14;
  assert.equal(winnerOf(state), null);
  state.off.white = 15;
  assert.equal(winnerOf(state), "white");
});
