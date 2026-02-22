export type DiffLine = { type: 'equal' | 'added' | 'removed'; text: string }

/**
 * LCS-based line diff.
 * Returns an array of DiffLine objects describing the changes from oldCode to newCode.
 */
export function diffLines(oldCode: string, newCode: string): DiffLine[] {
  const a = oldCode.split('\n')
  const b = newCode.split('\n')

  const m = a.length
  const n = b.length

  // Build LCS table
  const dp: number[][] = Array.from({ length: m + 1 }, () => new Array(n + 1).fill(0))
  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      if (a[i - 1] === b[j - 1]) {
        dp[i][j] = dp[i - 1][j - 1] + 1
      } else {
        dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1])
      }
    }
  }

  // Backtrack to reconstruct diff
  const result: DiffLine[] = []
  let i = m
  let j = n

  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && a[i - 1] === b[j - 1]) {
      result.push({ type: 'equal', text: a[i - 1] })
      i--
      j--
    } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
      result.push({ type: 'added', text: b[j - 1] })
      j--
    } else {
      result.push({ type: 'removed', text: a[i - 1] })
      i--
    }
  }

  return result.reverse()
}
