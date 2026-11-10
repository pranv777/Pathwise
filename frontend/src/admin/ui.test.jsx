import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { BarList, Kpi, LineChart, Pill, Table } from './ui'

describe('admin ui', () => {
  it('Kpi shows a dash when the value is missing', () => {
    render(<Kpi label="Success rate" value={null} hint="Overall success rate" tone="neutral" />)
    expect(screen.getByText('—')).toBeInTheDocument()
  })

  it('Pill renders its value', () => {
    render(<Pill value="suspended" />)
    expect(screen.getByText('suspended')).toBeInTheDocument()
  })

  it('Table shows the empty message and rows', () => {
    const cols = [{ key: 'name', label: 'Name' }]
    const onRow = () => {}
    const { rerender } = render(<Table cols={cols} rows={[]} empty="Nothing found" onRow={onRow} />)
    expect(screen.getByText('Nothing found')).toBeInTheDocument()
    rerender(
      <Table cols={cols} rows={[{ id: 1, name: 'Asha' }]} empty="Nothing found" onRow={onRow} />,
    )
    expect(screen.getByText('Asha')).toBeInTheDocument()
  })

  it('LineChart and BarList handle empty data', () => {
    render(
      <>
        <LineChart data={[]} />
        <BarList data={[]} />
      </>,
    )
    expect(screen.getAllByText('No data')).toHaveLength(2)
  })

  it('LineChart labels the first and last day', () => {
    render(
      <LineChart
        data={[
          { date: '2026-11-01', count: 1 },
          { date: '2026-11-02', count: 3 },
        ]}
      />,
    )
    expect(screen.getByText('2026-11-01')).toBeInTheDocument()
    expect(screen.getByText('2026-11-02')).toBeInTheDocument()
  })
})
