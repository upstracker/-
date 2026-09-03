; Universal offline installer: x86 payload on 32-bit Windows, x64 otherwise.

#define MyAppName "ระบบออกใบเบิกจ่ายแบตเตอรี่"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "คลังแบตเตอรี่และบริการ"
#define MyAppExeName "BatteryRequisition.exe"

[Setup]
; App Identity
AppId={{D37B4C8A-692B-4A19-952F-9C1D9F128E61}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
VersionInfoVersion=1.0.0.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName}
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}
DefaultDirName={userpf}\BatteryRequisitionApp
DefaultGroupName=ระบบออกใบเบิกแบตเตอรี่
AllowNoIcons=yes
OutputDir=dist_installer
OutputBaseFilename=BatteryRequisition_Setup_v1.0.0
SetupIconFile=assets\car_battery.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
UsePreviousAppDir=yes
CloseApplications=yes
RestartApplications=no

; บีบอัดไฟล์ตัวติดตั้งสูงสุดแบบ LZMA2
Compression=lzma2/ultra64
SolidCompression=yes

; กำหนดความเข้ากันได้ย้อนหลัง: รองรับตั้งแต่ Windows 7 SP1 ขึ้นไป (Kernel 6.1sp1)
MinVersion=6.1sp1
ArchitecturesAllowed=x86os or x64os

; สิทธิ์ในการติดตั้ง
PrivilegesRequired=lowest

; หน้าต่างแสดงผล
WizardStyle=modern dynamic
DisableWelcomePage=no
SetupLogging=yes

[Languages]
Name: "thai"; MessagesFile: "compiler:Languages\Thai.isl"

[Tasks]
Name: "desktopicon"; Description: "สร้างไอคอนบนหน้าจอ Desktop"; GroupDescription: "ตัวเลือกเพิ่มเติม:"; Flags: checkedonce

[Files]
Source: "dist_x86\BatteryRequisition\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Check: not IsWin64
Source: "dist_x64\BatteryRequisition\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Check: IsWin64

[Icons]
Name: "{userprograms}\ระบบออกใบเบิกแบตเตอรี่\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{userdesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon
Name: "{userprograms}\ระบบออกใบเบิกแบตเตอรี่\ถอนการติดตั้งโปรแกรม"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "เปิดใช้งานโปรแกรมทันที (Launch Application)"; Flags: nowait postinstall skipifsilent

[Code]
function LegacyWindowsRuntimePresent: Boolean;
var
  RuntimeDir: String;
begin
  if IsWin64 then
    RuntimeDir := ExpandConstant('{sysnative}')
  else
    RuntimeDir := ExpandConstant('{sys}');
  Result := FileExists(RuntimeDir + '\ucrtbase.dll') and
    FileExists(RuntimeDir + '\api-ms-win-crt-runtime-l1-1-0.dll');
end;

function InitializeSetup: Boolean;
begin
  Result := True;
  if (GetWindowsVersion < $0A000000) and (not LegacyWindowsRuntimePresent) then
  begin
    SuppressibleMsgBox(
      'Windows เครื่องนี้ยังขาด Universal C Runtime (KB2999226)' + #13#10 +
      'กรุณาติดตั้ง Windows Update ที่จำเป็น รีสตาร์ตเครื่อง แล้วเรียก Setup อีกครั้ง',
      mbCriticalError, MB_OK, IDOK);
    Result := False;
  end;
end;
