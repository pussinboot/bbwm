;; run this script to prevent default windows actions from happening :(

#SingleInstance force

;;;;;;;;;;;;
;; tiling ;;
;;;;;;;;;;;;

;; tile w/ default scheme
#Z:: Send !{F5}
;; untile
#X:: Send !{F6}
;; rotate tile type
#D:: Send !{F7}

;; tile horiz
#A:: Send !{F8}
;; tile vert
#S:: Send !{F9}
;; tile mono
#C:: Send ^{F6}


;; edit split ratios
#F:: Send !{F10}
;; draw menu
#Q:: Send !{F11}
;; draw workspaces
#W:: Send !{F12}

;;;;;;;;;;;;;;
;; movement ;;
;;;;;;;;;;;;;;

#up:: Send {Blind}#{F5}
#down:: Send {Blind}#{F6}
#left:: Send {Blind}#{F7}
#right:: Send {Blind}#{F8}

;;;;;;;;;;;;;;
;; swapping ;;
;;;;;;;;;;;;;;

#^up:: Send #{F9}
#^down:: Send #{F10}
#^left:: Send #{F11}
#^right:: Send #{F12}

;;;;;;;;;;;;;;;;
;; workspaces ;;
;;;;;;;;;;;;;;;;

^!1:: Send #{F2}
^!2:: Send #{F3}
^!3:: Send #{F4}

#Home:: Send !^{Home}