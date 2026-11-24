/**
 * Pure, deterministic backgammon rules engine.
 *
 * Board coordinates follow the existing PediGuardian UI:
 * white moves from point 0 toward 23; black moves from 23 toward 0.
 * Positive point counts are white checkers; negative counts are black.
 */
export type Player = "white" | "black";
export type MovePosition = number | "bar";
export type MoveDestination = number | "off";

export interface BackgammonMove {
  from: MovePosition;
  to: MoveDestination;
  die: number;
}

export interface BackgammonState {
  points: number[];
  bar: Record<Player, number>;
  off: Record<Player, number>;
}

const opponent = (player: Player): Player =>
  player === "white" ? "black" : "white";

const sign = (player: Player): number => (player === "white" ? 1 : -1);

function assertState(state: BackgammonState): void {
  if (!state || !Array.isArray(state.points) || state.points.length !== 24) {
    throw new TypeError("Backgammon state must contain exactly 24 points");
  }
  for (const value of state.points) {
    if (!Number.isInteger(value) || value < -15 || value > 15) {
      throw new TypeError("Point counts must be integers between -15 and 15");
    }
  }
  for (const player of ["white", "black"] as const) {
    if (!Number.isInteger(state.bar?.[player]) || state.bar[player] < 0 ||
        !Number.isInteger(state.off?.[player]) || state.off[player] < 0 ||
        state.bar[player] > 15 || state.off[player] > 15) {
      throw new TypeError("Bar and borne-off counts must be integers from 0 to 15");
    }
  }
}

export function initialBackgammonState(): BackgammonState {
  const state: BackgammonState = {
    points: Array(24).fill(0),
    bar: { white: 0, black: 0 },
    off: { white: 0, black: 0 },
  };
  state.points[0] = 2;
  state.points[11] = 5;
  state.points[16] = 3;
  state.points[18] = 5;
  state.points[5] = -5;
  state.points[7] = -3;
  state.points[12] = -5;
  state.points[23] = -2;
  return state;
}

export function countCheckers(
  state: BackgammonState,
  player: Player,
): number {
  assertState(state);
  const board = state.points.reduce(
    (sum, value) => sum + Math.max(0, value * sign(player)),
    0,
  );
  return board + state.bar[player] + state.off[player];
}

export function winnerOf(state: BackgammonState): Player | null {
  assertState(state);
  if (state.off.white >= 15) return "white";
  if (state.off.black >= 15) return "black";
  return null;
}

function isHomeBoard(state: BackgammonState, player: Player): boolean {
  if (state.bar[player] !== 0) return false;
  if (player === "white") {
    for (let i = 0; i < 18; i++) {
      if (state.points[i] > 0) return false;
    }
  } else {
    for (let i = 6; i < 24; i++) {
      if (state.points[i] < 0) return false;
    }
  }
  return true;
}

function isOpen(state: BackgammonState, point: number, player: Player): boolean {
  if (point < 0 || point > 23) return false;
  return state.points[point] * sign(player) >= -1;
}

function mayBearOffFrom(
  state: BackgammonState,
  player: Player,
  from: number,
  die: number,
): boolean {
  if (!isHomeBoard(state, player)) return false;
  const destination = from + sign(player) * die;
  const exact = player === "white" ? destination === 24 : destination === -1;
  if (exact) return true;

  const overshoots = player === "white" ? destination > 24 : destination < -1;
  if (!overshoots) return false;

  // An oversized die may bear off only when no checker is farther from
  // the exit than the checker being borne off.
  if (player === "white") {
    for (let i = from + 1; i < 24; i++) {
      if (state.points[i] > 0) return false;
    }
  } else {
    for (let i = from - 1; i >= 0; i--) {
      if (state.points[i] < 0) return false;
    }
  }
  return true;
}

export function legalMovesForDie(
  state: BackgammonState,
  player: Player,
  die: number,
): BackgammonMove[] {
  assertState(state);
  if (!Number.isInteger(die) || die < 1 || die > 6) {
    throw new RangeError("A die value must be an integer from 1 to 6");
  }

  const moves: BackgammonMove[] = [];
  const direction = sign(player);

  // Checkers on the bar have priority over every checker on the board.
  if (state.bar[player] > 0) {
    const entry = player === "white" ? die - 1 : 24 - die;
    if (isOpen(state, entry, player)) {
      moves.push({ from: "bar", to: entry, die });
    }
    return moves;
  }

  for (let from = 0; from < 24; from++) {
    if (state.points[from] * direction <= 0) continue;
    const to = from + direction * die;

    if (to >= 0 && to <= 23) {
      if (isOpen(state, to, player)) {
        moves.push({ from, to, die });
      }
      continue;
    }

    if (mayBearOffFrom(state, player, from, die)) {
      moves.push({ from, to: "off", die });
    }
  }
  return moves;
}

function cloneState(state: BackgammonState): BackgammonState {
  return {
    points: [...state.points],
    bar: { ...state.bar },
    off: { ...state.off },
  };
}

function sameMove(a: BackgammonMove, b: BackgammonMove): boolean {
  return a.from === b.from && a.to === b.to && a.die === b.die;
}

export function applyBackgammonMove(
  state: BackgammonState,
  player: Player,
  move: BackgammonMove,
): BackgammonState {
  assertState(state);
  const legal = legalMovesForDie(state, player, move.die);
  if (!legal.some((candidate) => sameMove(candidate, move))) {
    throw new Error("Illegal backgammon move");
  }

  const next = cloneState(state);
  const direction = sign(player);
  const other = opponent(player);

  if (move.from === "bar") {
    next.bar[player]--;
  } else {
    next.points[move.from] -= direction;
  }

  if (move.to === "off") {
    next.off[player]++;
  } else {
    if (next.points[move.to] === -direction) {
      next.points[move.to] = 0;
      next.bar[other]++;
    }
    next.points[move.to] += direction;
  }

  return next;
}

function normalizeDice(dice: number[]): number[] {
  if (!Array.isArray(dice) || (dice.length !== 2 && dice.length !== 4)) {
    throw new TypeError("A roll must contain two dice or four equal doubles");
  }
  if (dice.some((die) => !Number.isInteger(die) || die < 1 || die > 6)) {
    throw new RangeError("Each die must be an integer from 1 to 6");
  }
  if (dice.length === 4 && !dice.every((die) => die === dice[0])) {
    throw new TypeError("Four dice are valid only for doubles");
  }
  if (dice.length === 2 && dice[0] === dice[1]) {
    return [dice[0], dice[0], dice[0], dice[0]];
  }
  return [...dice].sort((a, b) => b - a);
}

function removeDie(dice: number[], index: number): number[] {
  return dice.filter((_value, current) => current !== index);
}

/**
 * Enumerates complete legal turn sequences and applies the mandatory-dice rules:
 * use as many dice as possible; if only one of two different dice can be used,
 * use the higher die when it is playable.
 */
export function legalTurnSequences(
  state: BackgammonState,
  player: Player,
  rolledDice: number[],
): BackgammonMove[][] {
  assertState(state);
  const dice = normalizeDice(rolledDice);
  const sequences: BackgammonMove[][] = [];

  const walk = (
    current: BackgammonState,
    remaining: number[],
    path: BackgammonMove[],
  ): void => {
    if (remaining.length === 0) {
      sequences.push(path);
      return;
    }

    let foundMove = false;
    const triedValues = new Set<number>();
    for (let index = 0; index < remaining.length; index++) {
      const die = remaining[index];
      if (triedValues.has(die)) continue;
      triedValues.add(die);

      const moves = legalMovesForDie(current, player, die);
      for (const move of moves) {
        foundMove = true;
        const next = applyBackgammonMove(current, player, move);
        walk(next, removeDie(remaining, index), [...path, move]);
      }
    }

    if (!foundMove) sequences.push(path);
  };

  walk(state, dice, []);
  const maxMoves = Math.max(0, ...sequences.map((sequence) => sequence.length));
  let best = sequences.filter((sequence) => sequence.length === maxMoves);

  if (dice.length === 2 && dice[0] !== dice[1] && maxMoves === 1) {
    const highDie = Math.max(dice[0], dice[1]);
    const higherDieSequences = best.filter(
      (sequence) => sequence[0]?.die === highDie,
    );
    if (higherDieSequences.length > 0) best = higherDieSequences;
  }

  return best;
}

export function applyTurnSequence(
  state: BackgammonState,
  player: Player,
  sequence: BackgammonMove[],
): BackgammonState {
  return sequence.reduce(
    (current, move) => applyBackgammonMove(current, player, move),
    cloneState(state),
  );
}
