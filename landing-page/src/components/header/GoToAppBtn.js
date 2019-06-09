import React from 'react'
import { Link } from 'gatsby'

function GoToAppBtn(props) {
  return (
    <Link to="/authentication">
      <div className="button">Go to app</div>
    </Link>
  )
}

export default GoToAppBtn
