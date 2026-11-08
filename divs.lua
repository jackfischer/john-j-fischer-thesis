-- Turn fenced divs with a class into LaTeX environments
function Div(el)
  local c = el.classes[1]
  if c then
    table.insert(el.content, 1, pandoc.RawBlock('latex', '\\begin{' .. c .. '}'))
    table.insert(el.content, pandoc.RawBlock('latex', '\\end{' .. c .. '}'))
    return el.content
  end
end
