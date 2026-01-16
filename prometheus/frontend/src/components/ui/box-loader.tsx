import type React from "react"

const Loader: React.FC = () => {
    return (
        <div className="box-loader-container">
            <div className="boxes">
                <div className="box box-1">
                    <div className="face face-front" />
                    <div className="face face-right" />
                    <div className="face face-top" />
                    <div className="face face-bottom" />
                </div>
                <div className="box box-2">
                    <div className="face face-front" />
                    <div className="face face-right" />
                    <div className="face face-top" />
                    <div className="face face-bottom" />
                </div>
                <div className="box box-3">
                    <div className="face face-front" />
                    <div className="face face-right" />
                    <div className="face face-top" />
                    <div className="face face-bottom" />
                </div>
                <div className="box box-4">
                    <div className="face face-front" />
                    <div className="face face-right" />
                    <div className="face face-top" />
                    <div className="face face-bottom" />
                </div>
            </div>
        </div>
    )
}

export default Loader
