import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { HexGauge } from './HexGauge'

describe('HexGauge', () => {
  it('shows the score and its band label', () => {
    render(<HexGauge score={84} />)
    expect(screen.getByText('84')).toBeInTheDocument()
    expect(screen.getByText('desert')).toBeInTheDocument()
  })

  it('has an accessible label describing the score', () => {
    render(<HexGauge score={12} />)
    expect(screen.getByRole('img')).toHaveAccessibleName(/desert score 12 out of 100, served/i)
  })
})
