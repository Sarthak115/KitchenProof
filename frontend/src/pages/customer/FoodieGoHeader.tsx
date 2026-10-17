import { Link } from 'react-router-dom'

/** FoodieGo is a made-up food delivery brand used as a mockup. */
export function FoodieGoHeader({ subtitle }: { subtitle?: string }) {
  return (
    <div className="bg-gradient-to-r from-rose-600 to-orange-500 text-white">
      <div className="mx-auto flex max-w-3xl items-center gap-3 px-4 py-3">
        <Link to="/customer" className="text-xl font-black italic tracking-tight">
          FoodieGo
        </Link>
        <span className="rounded bg-white/20 px-1.5 py-0.5 text-[10px] font-bold uppercase">mockup</span>
        {subtitle && <span className="ml-auto truncate text-sm text-white/90">{subtitle}</span>}
      </div>
    </div>
  )
}
