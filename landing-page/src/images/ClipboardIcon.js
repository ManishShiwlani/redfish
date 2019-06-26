import React from 'react'
import { css } from 'linaria'

const icon = css`
  height: 16px;
  width: 16px;
  margin-left: 8px;
  vertical-align: middle;
  fill: #444;
`

const ClipboardIcon = props => (
  <svg className={icon} {...props}>
    <path d="M9.66634 0.666687H1.66634C0.933008 0.666687 0.333008 1.26669 0.333008 2.00002V11.3334H1.66634V2.00002H9.66634V0.666687ZM11.6663 3.33335H4.33301C3.59967 3.33335 2.99967 3.93335 2.99967 4.66669V14C2.99967 14.7334 3.59967 15.3334 4.33301 15.3334H11.6663C12.3997 15.3334 12.9997 14.7334 12.9997 14V4.66669C12.9997 3.93335 12.3997 3.33335 11.6663 3.33335ZM11.6663 14H4.33301V4.66669H11.6663V14Z" />
  </svg>
)

export default ClipboardIcon