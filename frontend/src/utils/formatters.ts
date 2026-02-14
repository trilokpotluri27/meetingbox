// Utility functions for formatting values

/** Format seconds into MM:SS or HH:MM:SS */
export function formatDuration(seconds: number): string {
  const hrs = Math.floor(seconds / 3600)
  const mins = Math.floor((seconds % 3600) / 60)
  const secs = Math.floor(seconds % 60)

  if (hrs > 0) {
    return `${hrs}:${mins.toString().padStart(2, '0')}:${secs
      .toString()
      .padStart(2, '0')}`
  }
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

/** Format seconds into a human-readable duration (e.g. "30 minutes") */
export function formatMinutes(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  if (mins < 1) return 'Less than a minute'
  if (mins === 1) return '1 minute'
  return `${mins} minutes`
}

/** Format total seconds into hours for stats display */
export function formatHours(totalSeconds: number): number {
  return Math.round(totalSeconds / 3600)
}

/** Truncate text with ellipsis */
export function truncate(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text
  return text.slice(0, maxLength) + '…'
}
