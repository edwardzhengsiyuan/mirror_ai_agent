<#
.SYNOPSIS
    PowerShell helpers for administering BaZi Agent billing.

.DESCRIPTION
    Wraps the /admin/* endpoints so you don't have to remember the curl
    incantation. Reads the admin token and base URL from environment
    variables once per session.

.EXAMPLE
    # Load this file and set the session defaults:
    . .\scripts\admin.ps1
    Set-BillingAdmin -BaseUrl "https://demo.example.com" -Token "..."

    # Open a user (returns the one-time API key):
    New-BillingUser -UserId "u_alice" -InitialCredits 1000 -DisplayName "Alice"

    # Top up:
    Invoke-Topup -UserId "u_alice" -Amount 500 -Note "promo"

    # Inspect:
    Get-BillingUsers
    Get-BillingLedger -UserId "u_alice" -Limit 50
    Get-BillingPricing
    Set-BillingUserStatus -UserId "u_alice" -Status disabled

.NOTES
    Functions raise on non-2xx responses. Every JSON body is decoded for you.
#>

$script:BillingAdminConfig = @{
    BaseUrl = $env:BAZI_ADMIN_BASE_URL
    Token   = $env:DEMO_API_TOKEN
}

function Set-BillingAdmin {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)] [string] $BaseUrl,
        [Parameter(Mandatory)] [string] $Token
    )
    $script:BillingAdminConfig.BaseUrl = $BaseUrl.TrimEnd('/')
    $script:BillingAdminConfig.Token   = $Token
    Write-Host "[admin] base_url=$($script:BillingAdminConfig.BaseUrl)"
}

function _Bz-RequireConfig {
    if (-not $script:BillingAdminConfig.BaseUrl) {
        throw "BaseUrl not set. Run: Set-BillingAdmin -BaseUrl <url> -Token <token>"
    }
    if (-not $script:BillingAdminConfig.Token) {
        throw "Admin token not set. Run: Set-BillingAdmin -BaseUrl <url> -Token <token>"
    }
}

function _Bz-Headers {
    @{
        "Authorization" = "Bearer $($script:BillingAdminConfig.Token)"
        "Content-Type"  = "application/json; charset=utf-8"
    }
}

function _Bz-Invoke {
    param(
        [Parameter(Mandatory)] [string] $Method,
        [Parameter(Mandatory)] [string] $Path,
        $Body = $null,
        [int] $TimeoutSec = 30
    )
    _Bz-RequireConfig
    $url = "$($script:BillingAdminConfig.BaseUrl)$Path"
    $params = @{
        Method  = $Method
        Uri     = $url
        Headers = _Bz-Headers
        TimeoutSec = $TimeoutSec
    }
    if ($null -ne $Body) {
        $params["Body"] = ($Body | ConvertTo-Json -Depth 8 -Compress)
    }
    try {
        return Invoke-RestMethod @params
    } catch {
        $resp = $_.Exception.Response
        if ($resp -and $resp.GetResponseStream) {
            try {
                $reader = New-Object System.IO.StreamReader($resp.GetResponseStream())
                $detail = $reader.ReadToEnd()
                Write-Error "HTTP $($resp.StatusCode.value__): $detail"
            } catch {
                Write-Error $_
            }
        } else {
            Write-Error $_
        }
        throw
    }
}

function New-BillingUser {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)] [string] $UserId,
        [string] $DisplayName,
        [int] $InitialCredits = 0,
        [int] $DailyCreditsLimit,
        [string] $KeyLabel = "primary",
        [switch] $NoKey
    )
    $body = @{
        user_id           = $UserId
        initial_credits   = $InitialCredits
        issue_first_key   = -not $NoKey.IsPresent
    }
    if ($DisplayName)            { $body.display_name = $DisplayName }
    if ($KeyLabel)               { $body.key_label = $KeyLabel }
    if ($PSBoundParameters.ContainsKey('DailyCreditsLimit')) {
        $body.daily_credits_limit = $DailyCreditsLimit
    }
    $resp = _Bz-Invoke -Method POST -Path "/admin/users" -Body $body
    if ($resp.api_key) {
        Write-Host ""
        Write-Host "  api_key: $($resp.api_key)" -ForegroundColor Yellow
        Write-Host "  ^ Save this now. It will not be shown again." -ForegroundColor DarkYellow
        Write-Host ""
    }
    $resp
}

function Get-BillingUsers {
    [CmdletBinding()]
    param([int] $Limit = 200)
    (_Bz-Invoke -Method GET -Path "/admin/users?limit=$Limit").users
}

function Set-BillingUserStatus {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)] [string] $UserId,
        [Parameter(Mandatory)] [ValidateSet("active", "disabled")] [string] $Status
    )
    _Bz-Invoke -Method POST -Path "/admin/users/$UserId/status" -Body @{ status = $Status }
}

function Invoke-Topup {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)] [string] $UserId,
        [Parameter(Mandatory)] [int] $Amount,
        [string] $Note,
        [string] $RequestId,
        [string] $Source = "admin"
    )
    if ($Amount -le 0) { throw "Amount must be > 0 (credits, not RMB)." }
    $body = @{
        user_id        = $UserId
        amount_credits = $Amount
        source         = $Source
    }
    if ($Note)      { $body.note = $Note }
    if ($RequestId) { $body.request_id = $RequestId }
    _Bz-Invoke -Method POST -Path "/admin/topup" -Body $body
}

function Get-BillingLedger {
    [CmdletBinding()]
    param(
        [string] $UserId,
        [int] $Limit = 100
    )
    $qs = "limit=$Limit"
    if ($UserId) { $qs += "&user_id=$([uri]::EscapeDataString($UserId))" }
    (_Bz-Invoke -Method GET -Path "/admin/ledger?$qs").rows
}

function Get-BillingPricing {
    _Bz-Invoke -Method GET -Path "/admin/pricing"
}

function Get-BillingBalance {
    <#
    .SYNOPSIS
        Look up a user's balance via the admin user list (admin token only).
    #>
    [CmdletBinding()]
    param([Parameter(Mandatory)] [string] $UserId)
    $u = Get-BillingUsers | Where-Object { $_.user_id -eq $UserId } | Select-Object -First 1
    if (-not $u) { throw "User not found: $UserId" }
    $u | Select-Object user_id, balance_credits, status, daily_credits_limit
}

Write-Host "BaZi Agent admin helpers loaded. Run Get-Command -Module ... or:" -ForegroundColor Cyan
Write-Host "  Set-BillingAdmin, New-BillingUser, Invoke-Topup, Get-BillingUsers," -ForegroundColor Cyan
Write-Host "  Get-BillingLedger, Get-BillingPricing, Get-BillingBalance, Set-BillingUserStatus" -ForegroundColor Cyan
